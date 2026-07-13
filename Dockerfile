FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

# Define o diretório de instalação dos browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# 🔥 PRIMEIRO: Instala as dependências Python (incluindo Playwright)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 🔥 SEGUNDO: Instala o Chromium (agora o Playwright já está instalado)
RUN playwright install chromium

# Copia o resto do código
COPY . .

EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]