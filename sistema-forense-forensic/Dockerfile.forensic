# Dockerfile para el stack forense con Python 3.9
FROM python:3.9-slim-bullseye

# Instalar dependencias del sistema necesarias para herramientas forenses
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    pkg-config \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    libewf-dev \
    ewf-tools \
    afflib-tools \
    libmagic1 \
    libfuse-dev \
    libsqlite3-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libbz2-dev \
    liblzma-dev \
    libncurses5-dev \
    libreadline-dev \
    libgdbm-dev \
    libnss3-dev \
    libffi-dev \
    libssl-dev \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements específicos para el stack forense
COPY requirements_forensic.txt .

# Instalar dependencias de Python para herramientas forenses
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements_forensic.txt

# Instalar pyaff4 y dependencias específicas
RUN pip install --no-cache-dir \
    pyaff4 \
    pyewf \
    dfvfs \
    dfimagetools \
    libewf-python \
    aff4 \
    pytsk3 \
    pycryptodome \
    cryptography

# Crear directorios necesarios
RUN mkdir -p /app/forensic_data /app/logs /app/temp

# Exponer puerto
EXPOSE 5001

# Comando por defecto
CMD ["python", "forensic_agent.py"]
