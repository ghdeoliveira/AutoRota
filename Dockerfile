FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

WORKDIR /app

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 🔥 INSTALA O CHROMIUM DURANTE O BUILD
RUN playwright install chromium

EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]