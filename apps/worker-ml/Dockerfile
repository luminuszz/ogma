FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    python3.11 python3.11-dev python3-pip \
    libgl1 libglib2.0-0 \
    && apt-get remove -y python3-numpy python3-opencv 2>/dev/null || true \
    && rm -rf /var/lib/apt/lists/*

# Make python3.11 the default python
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python python3.11 1

# Use pip from python3.11
RUN python3.11 -m pip install --upgrade pip

WORKDIR /app

COPY requirements.txt .
RUN python3.11 -m pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DATA_DIR=/data

CMD ["python3.11", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
