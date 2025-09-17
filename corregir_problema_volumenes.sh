#!/bin/bash
# Script para corregir el problema de volúmenes entre stacks

echo "🔧 CORRIGIENDO PROBLEMA DE VOLÚMENES"
echo "===================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar mensajes con colores
show_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Verificar que forensic_agent.py existe
if [ ! -f "forensic_agent.py" ]; then
    show_message $RED "❌ forensic_agent.py no existe en el directorio actual"
    exit 1
fi

show_message $GREEN "✅ forensic_agent.py encontrado en el directorio actual"

# Crear directorio de respaldo si no existe
show_message $BLUE "📁 Creando directorio de respaldo..."
mkdir -p /mnt/Respaldo/sistema-forense

if [ $? -eq 0 ]; then
    show_message $GREEN "✅ Directorio de respaldo creado/verificado"
else
    show_message $RED "❌ Error creando directorio de respaldo"
    exit 1
fi

# Copiar forensic_agent.py al directorio de respaldo
show_message $BLUE "📋 Copiando forensic_agent.py al directorio de respaldo..."
cp forensic_agent.py /mnt/Respaldo/sistema-forense/

if [ $? -eq 0 ]; then
    show_message $GREEN "✅ forensic_agent.py copiado al directorio de respaldo"
else
    show_message $RED "❌ Error copiando forensic_agent.py al directorio de respaldo"
    exit 1
fi

# Verificar que el archivo esté en el directorio de respaldo
show_message $BLUE "🔍 Verificando archivo en directorio de respaldo..."
ls -la /mnt/Respaldo/sistema-forense/forensic_agent.py

if [ $? -eq 0 ]; then
    show_message $GREEN "✅ Archivo verificado en directorio de respaldo"
else
    show_message $RED "❌ Archivo no encontrado en directorio de respaldo"
    exit 1
fi

# Detener el contenedor forense
show_message $BLUE "🛑 Deteniendo contenedor forense..."
docker-compose -f STACK_FORENSE.yml down

# Modificar temporalmente el STACK_FORENSE.yml para usar el directorio de respaldo
show_message $BLUE "🔧 Modificando configuración del STACK_FORENSE..."

# Crear backup del archivo original
cp STACK_FORENSE.yml STACK_FORENSE.yml.backup

# Crear versión modificada que use el directorio de respaldo
cat > STACK_FORENSE_temp.yml << 'EOF'
# Docker Compose para Stack Forense (Solo Agente) - VERSIÓN MODIFICADA
version: '3.8'

services:
  forensic_agent:
    image: python:3.9-slim-bullseye
    container_name: forensic_agent
    working_dir: /app
    expose:
      - "5001"
    volumes:
      - /mnt/Respaldo/sistema-forense/forensic_data:/app/forensic_data
      - /mnt/Respaldo/sistema-forense/logs:/app/logs
      - /mnt/Respaldo/sistema-forense/temp:/app/temp
      - /mnt/Respaldo/sistema-forense:/app/host:ro
    environment:
      - AGENT_ID=forensic_agent_001
      - AGENT_NAME=Agente Forense Principal
      - DATABASE_URL=postgresql://forensic:forensic123@db:5432/sistema_forense
      - REDIS_URL=redis://redis:6379/0
      - PYTHONUNBUFFERED=1
    command: >
      sh -c "
        echo '=== CREANDO ESTRUCTURA DE DIRECTORIOS ===' &&
        mkdir -p /app/forensic_data /app/temp /app/logs &&
        echo '=== COPIANDO ARCHIVOS DEL AGENTE FORENSE ===' &&
        if [ -f /app/host/forensic_agent.py ]; then cp /app/host/forensic_agent.py /app/; fi &&
        if [ -d /app/host/utils_package ]; then cp -r /app/host/utils_package /app/; fi &&
        echo '=== INSTALANDO DEPENDENCIAS FORENSES ===' &&
        apt-get update && apt-get install -y build-essential gcc g++ make cmake pkg-config libffi-dev libssl-dev libpq-dev libewf-dev ewf-tools afflib-tools libmagic1 libfuse-dev libsqlite3-dev libxml2-dev libxslt1-dev zlib1g-dev libbz2-dev liblzma-dev libncurses5-dev libreadline-dev libgdbm-dev libnss3-dev wget curl git &&
        echo '=== INSTALANDO PYTHON FORENSE ===' &&
        pip install --no-cache-dir --upgrade pip setuptools wheel &&
        pip install --no-cache-dir Flask==2.3.3 gunicorn==21.2.0 requests psycopg2-binary redis flask-cors flask-login flask-limiter flask-sqlalchemy bcrypt python-magic psutil &&
        pip install --no-cache-dir pyaff4 pyewf dfvfs dfimagetools libewf-python aff4 pytsk3 pycryptodome cryptography &&
        echo '=== VERIFICANDO HERRAMIENTAS ===' &&
        ewfacquire --version || echo 'ewfacquire disponible' &&
        echo '=== VERIFICANDO ARCHIVO FORENSIC_AGENT ===' &&
        ls -la /app/forensic_agent.py &&
        echo '=== INICIANDO AGENTE ===' &&
        exec python forensic_agent.py
      "
    restart: always
    networks:
      - forense_network
    privileged: true

networks:
  forense_network:
    driver: bridge
EOF

# Iniciar el contenedor con la configuración modificada
show_message $BLUE "🚀 Iniciando contenedor con configuración modificada..."
docker-compose -f STACK_FORENSE_temp.yml up -d

if [ $? -eq 0 ]; then
    show_message $GREEN "✅ Contenedor iniciado con configuración modificada"
else
    show_message $RED "❌ Error iniciando contenedor con configuración modificada"
    exit 1
fi

# Esperar a que se inicie
show_message $BLUE "⏳ Esperando que el contenedor se inicie..."
sleep 20

# Verificar que esté corriendo
show_message $BLUE "🔍 Verificando estado del contenedor..."
docker ps | grep forensic_agent

# Verificar que el archivo esté en el contenedor
show_message $BLUE "🔍 Verificando archivo en el contenedor..."
docker exec forensic_agent ls -la /app/forensic_agent.py

if [ $? -eq 0 ]; then
    show_message $GREEN "✅ forensic_agent.py encontrado en el contenedor"
else
    show_message $RED "❌ forensic_agent.py no encontrado en el contenedor"
fi

# Verificar logs
show_message $BLUE "📋 Logs del contenedor:"
docker logs forensic_agent --tail=15

# Probar la API
show_message $BLUE "🌐 Probando API del agente:"
curl -s http://localhost:5001/status 2>/dev/null

if [ $? -eq 0 ]; then
    show_message $GREEN "✅ API del agente responde correctamente"
else
    show_message $YELLOW "⚠️ API del agente no responde aún"
fi

# Restaurar archivo original
show_message $BLUE "🔄 Restaurando configuración original..."
mv STACK_FORENSE.yml.backup STACK_FORENSE.yml
rm -f STACK_FORENSE_temp.yml

echo ""
show_message $GREEN "🎉 ¡CORRECCIÓN COMPLETADA!"
echo "============================="
