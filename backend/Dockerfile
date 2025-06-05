# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies required for piper-tts and nginx
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    nginx \
    supervisor \
    openssl \
    certbot \
    python3-certbot-nginx \
    cron \
    espeak-ng \
    espeak-ng-data \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies FIRST
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install piper-tts binary AFTER Python packages
RUN wget -O /tmp/piper.tar.gz https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz \
    && tar -xzf /tmp/piper.tar.gz -C /tmp/ \
    && mv /tmp/piper /usr/local/bin/piper \
    && chmod +x /usr/local/bin/piper \
    && rm -rf /tmp/piper.tar.gz /tmp/piper_phonemize

# Copy application code
COPY app.py .
COPY gunicorn.conf.py .
COPY docker-entrypoint.sh .

# Copy configuration files
COPY nginx.conf /etc/nginx/sites-available/default
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create necessary directories
RUN mkdir -p piper_data outputs logs /var/log/supervisor

# Set permissions for nginx
RUN chown -R www-data:www-data /var/log/nginx /var/lib/nginx

# Create subdirectories for different languages
RUN mkdir -p piper_data/en_US piper_data/en_GB piper_data/es_ES piper_data/es_MX

# Download English US voices
RUN curl -L -o piper_data/en_US/en_US-lessac-medium.onnx https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx && \
    curl -L -o piper_data/en_US/en_US-lessac-medium.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

RUN curl -L -o piper_data/en_US/en_US-lessac-high.onnx https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/high/en_US-lessac-high.onnx && \
    curl -L -o piper_data/en_US/en_US-lessac-high.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/high/en_US-lessac-high.onnx.json

RUN curl -L -o piper_data/en_US/en_US-amy-high.onnx https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/high/en_US-amy-high.onnx && \
    curl -L -o piper_data/en_US/en_US-amy-high.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/high/en_US-amy-high.onnx.json

# Download English GB voices
RUN curl -L -o piper_data/en_GB/en_GB-alba-high.onnx https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alba/high/en_GB-alba-high.onnx && \
    curl -L -o piper_data/en_GB/en_GB-alba-high.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alba/high/en_GB-alba-high.onnx.json

# Download Spanish ES voices
RUN curl -L -o piper_data/es_ES/es_ES-maragda-high.onnx https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/maragda/high/es_ES-maragda-high.onnx && \
    curl -L -o piper_data/es_ES/es_ES-maragda-high.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/maragda/high/es_ES-maragda-high.onnx.json

# Download Spanish MX voices  
RUN curl -L -o piper_data/es_MX/es_MX-ald-high.onnx https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_MX/ald/high/es_MX-ald-high.onnx && \
    curl -L -o piper_data/es_MX/es_MX-ald-high.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_MX/ald/high/es_MX-ald-high.onnx.json

# Expose ports (80 for HTTP, 443 for HTTPS)
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

# Use the entrypoint script
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]