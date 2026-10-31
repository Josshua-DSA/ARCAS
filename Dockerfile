# ==============================================================================
# FinNews / ARCAS - Production Dockerfile
# Lightweight container for FastAPI REST service
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies (curl for healthcheck & debugging)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies with caching
#
# Torch dipasang lebih dulu dari indeks CPU, SEBELUM requirements.txt.
# Alasannya: `requirements.txt` menyebut `torch>=2.0.0` tanpa indeks, sehingga
# pip menarik roda default yang di PyPI sudah membawa CUDA (~2 GB: nvidia-*).
# Di container tanpa GPU itu bobot mati — tidak pernah dipakai, hanya
# memperbesar image. Memasang roda CPU lebih dulu membuat pip menganggap
# syarat `torch>=2.0.0` sudah terpenuhi, jadi requirements.txt tidak menarik
# ulang versi CUDA. Lingkungan GPU di mesin host tidak terpengaruh karena
# berkas ini hanya untuk image.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch && \
    pip install --no-cache-dir -r requirements.txt

# Create a non-root user for security best practices
#
# `chown -R /app` DILAKUKAN SEBELUM `COPY . .`. Kalau dibalik, setiap berkas
# hasil COPY harus disalin ulang ke layer baru hanya untuk mengubah
# kepemilikannya. Dengan bobot model ~3 GB di dalam konteks, urutan yang salah
# menambah ~3,9 GB layer sia-sia (terbukti di build cache: entri `useradd &&
# chown` sebesar 3,92 GB). Membuat user lebih dulu membuat COPY langsung
# menulis dengan pemilik yang benar.
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data /app/outputs && \
    chown -R appuser:appuser /app

# Copy application codebase
COPY --chown=appuser:appuser . .

USER appuser

# Expose FastAPI default port
EXPOSE 8000

# Healthcheck checking /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start FastAPI server via uvicorn factory
CMD ["uvicorn", "backend.src.serve.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
