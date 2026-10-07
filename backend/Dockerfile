FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# tesseract e poppler são necessários para o fallback de OCR.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# A aplicação não roda como root; o volume de storage pertence a ela.
RUN useradd --create-home --uid 1000 notas \
    && mkdir -p /app/storage/uploads /app/storage/outputs /app/storage/timbrados \
    && chown -R notas:notas /app

USER notas

EXPOSE 8000

# http.client em vez de httpx: a checagem roda a cada 30s (~2.9k vezes por dia)
# e importar httpx arrasta httpcore, h11, anyio e certifi a cada execução.
# A verificação é a mesma — GET /api/health, 200 = saudável.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import http.client,sys; c=http.client.HTTPConnection('127.0.0.1',8000,timeout=4); c.request('GET','/api/health'); sys.exit(0 if c.getresponse().status==200 else 1)"

# --proxy-headers faz o IP real do cliente (X-Forwarded-For) chegar ao
# rate limiting e ao audit_log, já que a aplicação roda atrás do nginx e
# do proxy do Coolify.
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*", \
     "--workers", "1"]
