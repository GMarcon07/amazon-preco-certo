FROM python:3.12-slim

# Evitar prompts interativos no apt
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Madrid

WORKDIR /app

# Instalar dependências de sistema para o Chromium / Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar o Chromium do Playwright com todas as dependências de sistema necessárias
RUN playwright install --with-deps chromium

# Copiar o restante código do projeto
COPY . .

# Criar diretório para persistência da base de dados SQLite
RUN mkdir -p /app/data

# Comando de arranque padrão: modo contínuo 24/7
CMD ["python", "run.py", "--daemon"]
