import asyncio
import pickle
import io
import secrets
from threading import Lock

import uvicorn
from fastapi import FastAPI, HTTPException, Path, Request, Response
from pydantic import BaseModel

from starlette.responses import StreamingResponse

from manga_translator import MangaTranslator

# AQUI ESTÁ A CORREÇÃO DO BUG: 'fractions' adicionado à lista de módulos permitidos
SAFE_PICKLE_MODULES = frozenset({
    'builtins',
    'collections',
    'numpy',
    'numpy.core.multiarray',
    'numpy.dtype',
    'manga_translator',
    'manga_translator.utils',
    'manga_translator.utils.generic',
    'manga_translator.config',
    'fractions'
})

class RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str):
        if module in SAFE_PICKLE_MODULES or module.startswith('PIL.'):
            return super().find_class(module, name)
        raise pickle.UnpicklingError(
            f"Deserialization of {module}.{name} is not allowed"
        )


def restricted_loads(data: bytes):
    return RestrictedUnpickler(io.BytesIO(data)).load()

class MethodCall(BaseModel):
    method_name: str
    attributes: bytes


class MangaShare:
    def __init__(self, params: dict = None):
        self.manga = MangaTranslator(params)
        self.host = params.get('host', '127.0.0.1')
        self.port = int(params.get('port', '5003'))
        nonce = params.get('nonce', None)
        if not nonce:
            nonce = secrets.token_hex(16)
        if nonce == "None":
            nonce = None
        self.nonce = nonce

        # each chunk has a structure like this status_code(int/1byte),len(int/4bytes),bytechunk
        # status codes are 0 for result, 1 for progress report, 2 for error
        self.progress_queue = asyncio.Queue()
        self.lock = Lock()

        async def hook(state: str, finished: bool):
            state_data = state.encode("utf-8")
            progress_data = b'\x01' + len(state_data).to_bytes(4, 'big') + state_data
            await self.progress_queue.put(progress_data)
            await asyncio.sleep(0)

        self.manga.add_progress_hook(hook)

    async def progress_stream(self):
        """
        loops until the status is != 1 which is eiter an error or the result
        """
        while True:
            progress = await self.progress_queue.get()
            yield progress
            if progress[0] != 1:
                break

    async def run_method(self, method, **attributes):
        try:
            if asyncio.iscoroutinefunction(method):
                result = await method(**attributes)
            else:
                result = method(**attributes)

            # Check if placeholder is used, if so create a minimal result object
            if hasattr(result, 'use_placeholder') and result.use_placeholder:
                from manga_translator import Context
                from PIL import Image
                minimal_result = Context()
                minimal_result.result = Image.new('RGB', (1, 1), color='white')
                minimal_result.use_placeholder = True
                result_bytes = pickle.dumps(minimal_result)
            else:
                result_bytes = pickle.dumps(result)

            encoded_result = b'\x00' + len(result_bytes).to_bytes(4, 'big') + result_bytes
            await self.progress_queue.put(encoded_result)
        except Exception as e:
            err_bytes = str(e).encode("utf-8")
            encoded_result = b'\x02' + len(err_bytes).to_bytes(4, 'big') + err_bytes
            await self.progress_queue.put(encoded_result)
        finally:
            self.lock.release()

    def check_nonce(self, request: Request):
        if self.nonce:
            nonce = request.headers.get('X-Nonce')
            if nonce != self.nonce:
                raise HTTPException(401, detail="Nonce does not match")

    def check_lock(self):
        if not self.lock.acquire(blocking=False):
            raise HTTPException(status_code=429, detail="some Method is already being executed.")

    def get_fn(self, method_name: str):
        if method_name.startswith("__"):
            raise HTTPException(status_code=403, detail="These functions are not allowed to be executed remotely")
        method = getattr(self.manga, method_name, None)
        if not method:
            raise HTTPException(status_code=404, detail="Method not found")
        return method

    async def listen(self, translation_params: dict = None):
        app = FastAPI()

        @app.get("/is_locked")
        async def is_locked():
            if self.lock.locked():
                return {"locked": True}
            return {"locked": False}

        @app.post("/simple_execute/{method_name}")
        async def execute_method(request: Request, method_name: str = Path(...)):
            self.check_nonce(request)
            self.check_lock()
            method = self.get_fn(method_name)
            attr = restricted_loads(await request.body())
            try:
                if asyncio.iscoroutinefunction(method):
                    result = await method(**attr)
                else:
                    result = method(**attr)
                self.lock.release()
                result_bytes = pickle.dumps(result)
                return Response(content=result_bytes, media_type="application/octet-stream")
            except Exception as e:
                self.lock.release()
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/execute/{method_name}")
        async def execute_method(request: Request, method_name: str = Path(...)):
            self.check_nonce(request)
            self.check_lock()
            method = self.get_fn(method_name)
            attr = restricted_loads(await request.body())

            config = attr.get('config')
            self.manga._is_streaming_mode = getattr(config, '_web_frontend_optimized', False) if config else False

            streaming_response = StreamingResponse(self.progress_stream(), media_type="application/octet-stream")
            asyncio.create_task(self.run_method(method, **attr))
            return streaming_response

        config = uvicorn.Config(app, host=self.host, port=self.port)
        server = uvicorn.Server(config)
        await server.serve()

import json
from typing import Mapping, Optional, Callable

import aiohttp
from PIL.Image import Image

from manga_translator import Config

NotifyType = Optional[Callable[[int, Optional[bytes]], None]]

async def fetch_data_stream(url, image: Image, config: Config, sender: NotifyType, headers: Mapping[str, str] = {}):
    attributes = {"image": image, "config": config}
    data = pickle.dumps(attributes)

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, headers=headers) as response:
            if response.status == 200:
                await process_stream(response, sender)
            else:
                raise HTTPException(response.status, detail=await response.text())

async def fetch_data(url, image: Image, config: Config, headers: Mapping[str, str] = {}):
    attributes = {"image": image, "config": config}
    data = pickle.dumps(attributes)

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, headers=headers) as response:
            if response.status == 200:
                try:
                    return pickle.loads(await response.read())
                except Exception as e:
                    raise HTTPException(502, detail=f'Invalid Pickle response from upstream: {e}')
            else:
                raise HTTPException(response.status, detail=await response.text())

async def process_stream(response, sender: NotifyType):
    buffer = b''

    async for chunk in response.content.iter_any():
        if chunk:
            buffer += chunk
            buffer = handle_buffer(buffer, sender)

def handle_buffer(buffer, sender: NotifyType):
    while len(buffer) >= 5:
        status, expected_size = extract_header(buffer)

        if len(buffer) >= 5 + expected_size:
            data = buffer[5:5 + expected_size]
            sender(status, data)
            buffer = buffer[5 + expected_size:]
        else:
            break
    return buffer

def extract_header(buffer):
    """Extract the status and expected size from the buffer."""
    status = int.from_bytes(buffer[0:1], byteorder='big')
    expected_size = int.from_bytes(buffer[1:5], byteorder='big')
    return status, expected_size
