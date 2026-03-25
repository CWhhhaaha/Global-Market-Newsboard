FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY README.md .
COPY NOTICE .
COPY LICENSE .

RUN mkdir -p /app/data /app/logs

EXPOSE 8010

CMD ["sh", "-c", "uvicorn src.market_stream.app:app --host ${MARKET_STREAM_HOST:-0.0.0.0} --port ${PORT:-8010}"]
