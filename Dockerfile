# Usa a imagem oficial do Playwright com Python
FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

# Define o diretório de instalação dos browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# 🔥 INSTALA O CHROMIUM DURANTE O BUILD (FORÇADO)
RUN playwright install chromium

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]