FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y default-libmysqlclient-dev build-essential pkg-config curl

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
