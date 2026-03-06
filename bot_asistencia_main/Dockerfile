# Archivo Docker
FROM python:3.10-slim

WORKDIR /app

# asyncpg se compila con gcc, no necesita deps de MySQL
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
