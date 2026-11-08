FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for compiling FastEmbed vector math libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set permanent environment variables inside the image container paths
ENV HF_HOME=/app/hf_cache
ENV FASTEMBED_CACHE_PATH=/app/fastembed_cache

# Copy the cache script and execute it DURING THE BUILD PHASE
COPY app/download_models.py .
RUN /usr/local/bin/python download_models.py

# Copy your actual Streamlit user interface code
COPY app/ .

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
