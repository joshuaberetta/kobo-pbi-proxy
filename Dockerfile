FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

RUN chmod +x src/scripts/entrypoint.sh

ENTRYPOINT ["sh", "src/scripts/entrypoint.sh"]
