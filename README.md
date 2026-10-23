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
- **Frontend:** React, TypeScript, Vite, TailwindCSS, TanStack React Query, Lucide Icons.
- **Backend:** FastAPI (Python), PostgreSQL, Redis, BullMQ / Arq.
- **IA e Tradução:** `manga-image-translator` (YOLOv8, PaddleOCR, LaMa Inpainting, Gemini 2.5 Flash via OpenRouter).
- **Web Scraping:** Playwright Chromium headless, BeautifulSoup4, httpx.
- **Armazenamento:** Cloudflare R2 (S3-compatible) para hospedagem ultrarrápida de imagens.
- **Infraestrutura:** Docker e Docker Compose (com suporte a aceleração por GPU NVIDIA).

## ✨ Principais Funcionalidades

### 🌐 Módulo Extensível de Scrapers & Valir Scans
- **Arquitetura Plugável (`BaseProvider`):** Suporte nativo ao [MangaDex](https://mangadex.org/), [Lycantoons](https://lycantoons.com/) e [Valir Scans](https://valirscans.org/), expansível para novos sites via `ProviderRegistry`.
- **Vinculação Inteligente de Obras:** Detecta semelhança entre obras importadas de fontes estrangeiras e títulos já existentes na sua biblioteca, permitindo mesclar capítulos inéditos em uma única obra sem duplicar registros.
- **Bypass de Proteções:** Suporte a headless browser (Playwright) e paginação completa de capítulos.

### 👁️ Tradução Multimodal com Visão Computacional (Gemini 2.5 Flash)
- **Concordância de Gênero Visual:** Envia a imagem renderizada da página junto com os segmentos de texto para o modelo multimodal (`google/gemini-2.5-flash`), permitindo que a IA inspecione visualmente quem está falando no quadrinho e aplique a concordância gramatical correta em português (ex: *"fui a única que sobreviveu"*, *"obrigada"*, *"cansada"*).
- **Tradução Fiel e Fluida:** Prompting avançado de 4 etapas (literal, desverbalização, refinamento cultural e polimento de concordância).

### 💬 Typesetting e Renderização Inteligente de Balões
- **Sem Estouro de Balão:** Trava estrita de delimitação (`dst_points = region.min_rect`), eliminando o bug de alargamento horizontal que vazava o texto para fora dos balões redondos.
- **Redução Proporcional de Fonte:** Quando a tradução em português requer mais linhas, a fonte é redimensionada proporcionalmente para se ajustar perfeitamente ao espaço original.
- **Centralização e Hifenação:** Alinhamento centralizado em balões de diálogo e separação silábica natural de palavras longas em português.

### 💰 Monitor de Créditos do OpenRouter em Tempo Real
- **Badge no Header da Home:** Exibe o saldo restante em dólares (`$X.XX`) diretamente no cabeçalho principal.
- **Indicador de Status por Cores:**
  - 🟢 **Verde:** Saldo $\ge \$2.00$
  - 🟡 **Amarelo:** Saldo $< \$2.00$
  - 🔴 **Vermelho:** Saldo $< \$0.50$
- **Tooltip Detalhado:** Exibe gasto do dia atual, gasto acumulado total e limite da chave ao passar o mouse.
- **Atualização Reativa (SSE):** O saldo é invalidado e atualizado instantaneamente a cada página traduzida via Server-Sent Events, além de suporte a refresh manual.

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

   # Inteligência Artificial (Tradução Multimodal LLM)
   OPENROUTER_API_KEY=sk-or-v1-...
   CUSTOM_OPENAI_MODEL=google/gemini-2.5-flash
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
