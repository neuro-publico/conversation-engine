# Usar una imagen base de Python
FROM python:3.10-slim

# jemalloc: returns freed memory to OS (glibc doesn't)
RUN apt-get update && apt-get install -y --no-install-recommends libjemalloc2 \
    && rm -rf /var/lib/apt/lists/* \
    && find /usr/lib -name "libjemalloc.so.2" -print -quit > /etc/jemalloc_path

ENV PYTHONUNBUFFERED=1

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar los archivos de requerimientos
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Exponer el puerto
EXPOSE 8000

# Comando para ejecutar la aplicación con jemalloc
CMD ["sh", "-c", "export LD_PRELOAD=$(cat /etc/jemalloc_path) && export MALLOC_CONF='background_thread:true,metadata_thp:auto,dirty_decay_ms:3000,muzzy_decay_ms:3000' && exec python main.py"]
