<div align="center">
  <img src="public/assets/cover.jpg" alt="Ogma Cover" width="100%" style="border-radius: 12px; margin-bottom: 20px;">
  
  # Ogma: Manga Translator & Reader
  
  **A premium, autonomous translation and reading experience for Manga, Manhwa, and Webtoons.**
</div>

## 📖 Descrição
**Ogma** é uma aplicação completa (Web App) focada em baixar, traduzir automaticamente através de IA, e disponibilizar mangás para leitura confortável. Integrando-se diretamente ao [MangaDex](https://mangadex.org/), o Ogma extrai capítulos crus, utiliza Modelos de Visão Computacional e OCR para detectar balões de texto, traduz os textos localmente ou via APIs de LLMs (como Ollama/OpenRouter) e renderiza as páginas traduzidas perfeitamente (Typesetting) sem que você precise editar uma única imagem.

## 🚀 Motivação
A tradução de mangás e webtoons independentes sempre foi um processo lento e braçal, dependendo de grupos de scanlation. Com a evolução da Inteligência Artificial em Visão Computacional (YOLO, PaddleOCR) e em LLMs, surgiu a oportunidade de criar um tradutor **on-demand e automatizado**. O objetivo do Ogma é permitir que leitores consumam conteúdo no exato instante de lançamento original, quebrando a barreira do idioma com alta fidelidade visual.

## ⚙️ Tecnologias Utilizadas
- **Frontend:** React, TypeScript, Vite, TailwindCSS, TanStack React Query.
- **Backend:** FastAPI (Python), PostgreSQL, Redis, BullMQ (Arq).
- **IA e Tradução:** `manga-image-translator` (YOLOv8, PaddleOCR, Lama Inpainting, Llama/GPT-4o).
- **Armazenamento:** Cloudflare R2 (S3-compatible) para hospedagem ultrarrápida de imagens.
- **Infraestrutura:** Docker e Docker Compose (Nvidia GPU Support).

## 🛠️ Instalação

### Pré-requisitos
- [Docker](https://www.docker.com/) e Docker Compose instalados.
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) (recomendado para aceleração de GPU na tradução).
- Conta no Cloudflare R2 (ou AWS S3) e no OpenRouter/Ollama.

### Passo-a-passo
1. **Clone o repositório:**
   ```bash
   git clone https://github.com/seu-usuario/ogma.git
   cd ogma
   ```

2. **Configure as Variáveis de Ambiente:**
   Crie um arquivo `.env` na raiz do projeto contendo as seguintes credenciais:
   ```env
   # Banco de Dados e Fila
   DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/ogma
   REDIS_URL=redis://default:pass@host:6379/0

   # Cloudflare R2 (Armazenamento das Imagens Traduzidas)
   R2_ACCOUNT_ID=seu_account_id
   R2_ENDPOINT_URL=https://seu_account_id.r2.cloudflarestorage.com
   R2_ACCESS_KEY_ID=seu_access_key
   R2_SECRET_ACCESS_KEY=seu_secret_key
   R2_BUCKET_NAME=ogma-storage
   R2_PUBLIC_URL=https://seu-dominio-r2.com

   # Inteligência Artificial (Tradução LLM)
   OPENROUTER_API_KEY=sk-or-v1-...
   CUSTOM_OPENAI_MODEL=nousresearch/hermes-3-llama-3.1-70b
   ```

3. **Inicie os Contêineres:**
   ```bash
   docker compose up -d
   ```
   *Isso irá subir a API (FastAPI), o Worker (Arq/Python), o tradutor de imagens e a interface Web.*

4. **Acesse a Aplicação:**
   Abra seu navegador em `http://localhost:3030`.

## 🖥️ Uso

1. **Biblioteca e Busca:** Na tela inicial, clique em "Baixar Novo Capítulo".
2. **Insira o Link:** Cole a URL de um capítulo do MangaDex ou seu respectivo ID.
3. **Selecione o Idioma:** A aplicação tentará inferir o idioma original automaticamente (Auto), mas você pode forçar para Inglês, Japonês, Espanhol, etc.
4. **Tradução em Background:** O backend irá mapear as páginas, baixar os originais, remover o texto estrangeiro usando Inpainting, traduzir via LLM e desenhar o novo texto (Typesetting) com a fonte `animeace.ttf`.
5. **Leitura:** As imagens prontas aparecem instantaneamente na sua tela com modo de rolagem infinita (Webtoon) ou por páginas.

## 📸 Prints do Projeto

> Exemplos de interface da aplicação:

### A Biblioteca (Home Screen)
<img src="public/assets/home.png" alt="Ogma Library" width="800">

### Modal de Busca e Resultados
<img src="public/assets/modal.png" alt="Ogma Search Modal" width="800">

---
*Ogma - Criado com foco na arte de ler histórias sem barreiras linguísticas.*
