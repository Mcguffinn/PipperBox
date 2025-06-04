# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies required for piper-tts
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install piper-tts binary
RUN wget -O /tmp/piper.tar.gz https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz \
    && tar -xzf /tmp/piper.tar.gz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/piper \
    && rm /tmp/piper.tar.gz

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Create necessary directories
RUN mkdir -p piper_data outputs

# Create subdirectories for different languages
RUN mkdir -p piper_data/en_US piper_data/en_GB piper_data/es_ES piper_data/es_MX

# Download English US voices
RUN wget -q -O piper_data/en_US/en_US-lessac-medium.onnx https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx && \
    wget -q -O piper_data/en_US/en_US-lessac-medium.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

RUN wget -q -O piper_data/en_US/en_US-lessac-high.onnx https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/high/en_US-lessac-high.onnx && \
    wget -q -O piper_data/en_US/en_US-lessac-high.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/high/en_US-lessac-high.onnx.json

RUN wget -q -O piper_data/en_US/en_US-amy-high.onnx https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/high/en_US-amy-high.onnx && \
    wget -q -O piper_data/en_US/en_US-amy-high.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/high/en_US-amy-high.onnx.json

# Download English GB voices
RUN wget -q -O piper_data/en_GB/en_GB-alba-high.onnx https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alba/high/en_GB-alba-high.onnx && \
    wget -q -O piper_data/en_GB/en_GB-alba-high.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alba/high/en_GB-alba-high.onnx.json

# Download Spanish ES voices
RUN wget -q -O piper_data/es_ES/es_ES-maragda-high.onnx https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/maragda/high/es_ES-maragda-high.onnx && \
    wget -q -O piper_data/es_ES/es_ES-maragda-high.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/maragda/high/es_ES-maragda-high.onnx.json

# Download Spanish MX voices  
RUN wget -q -O piper_data/es_MX/es_MX-ald-high.onnx https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_MX/ald/high/es_MX-ald-high.onnx && \
    wget -q -O piper_data/es_MX/es_MX-ald-high.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_MX/ald/high/es_MX-ald-high.onnx.json

# Expose port
EXPOSE 5600

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5600/ || exit 1

# Run the application
CMD ["python", "app.py"]