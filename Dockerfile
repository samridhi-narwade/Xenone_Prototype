# Use slim Python base — much smaller than default
FROM python:3.11-slim

WORKDIR /app

# Install only the system libraries chromadb/hnswlib needs to compile
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (so Docker caches this layer)
COPY requirements.txt .

# Step 1: Install CPU-only PyTorch (~180MB vs ~2.2GB for CUDA)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Step 2: Install everything else
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

CMD ["python", "run_both.py"]
