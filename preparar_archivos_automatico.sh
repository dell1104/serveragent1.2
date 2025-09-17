#!/bin/bash
# Script para preparar archivos automáticamente antes del despliegue

echo "🔧 PREPARANDO ARCHIVOS PARA DESPLIEGUE AUTOMÁTICO"
echo "================================================"

# Crear directorio de respaldo si no existe
echo "📁 Creando directorio de respaldo..."
mkdir -p /mnt/Respaldo/sistema-forense

# Copiar archivos necesarios al directorio de respaldo
echo "📋 Copiando archivos al directorio de respaldo..."

# Archivos del sistema principal
cp app.py /mnt/Respaldo/sistema-forense/ 2>/dev/null || echo "⚠️ app.py no encontrado"
cp models.py /mnt/Respaldo/sistema-forense/ 2>/dev/null || echo "⚠️ models.py no encontrado"
cp config.py /mnt/Respaldo/sistema-forense/ 2>/dev/null || echo "⚠️ config.py no encontrado"
cp security_config.py /mnt/Respaldo/sistema-forense/ 2>/dev/null || echo "⚠️ security_config.py no encontrado"
cp security_middleware.py /mnt/Respaldo/sistema-forense/ 2>/dev/null || echo "⚠️ security_middleware.py no encontrado"
cp requirements.txt /mnt/Respaldo/sistema-forense/ 2>/dev/null || echo "⚠️ requirements.txt no encontrado"
cp init_db.sql /mnt/Respaldo/sistema-forense/ 2>/dev/null || echo "⚠️ init_db.sql no encontrado"

# Archivo del agente forense
cp forensic_agent.py /mnt/Respaldo/sistema-forense/ 2>/dev/null || echo "⚠️ forensic_agent.py no encontrado"

# Copiar directorios
if [ -d "blueprints" ]; then
    echo "📁 Copiando blueprints..."
    cp -r blueprints /mnt/Respaldo/sistema-forense/
fi

if [ -d "templates" ]; then
    echo "📁 Copiando templates..."
    cp -r templates /mnt/Respaldo/sistema-forense/
fi

if [ -d "static" ]; then
    echo "📁 Copiando static..."
    cp -r static /mnt/Respaldo/sistema-forense/
fi

if [ -d "dist" ]; then
    echo "📁 Copiando dist..."
    cp -r dist /mnt/Respaldo/sistema-forense/
fi

if [ -d "instaladores" ]; then
    echo "📁 Copiando instaladores..."
    cp -r instaladores /mnt/Respaldo/sistema-forense/
fi

if [ -d "utils_package" ]; then
    echo "📁 Copiando utils_package..."
    cp -r utils_package /mnt/Respaldo/sistema-forense/
fi

# Crear directorios necesarios
echo "📁 Creando directorios necesarios..."
mkdir -p /mnt/Respaldo/sistema-forense/{casos_data,logs,static/uploads,agentes_data,json,forensic_data,temp}

echo "✅ Archivos preparados para despliegue automático"
echo "🚀 Ahora puedes ejecutar: docker-compose -f STACK_PRINCIPAL.yml up -d"
echo "🚀 Y luego: docker-compose -f STACK_FORENSE.yml up -d"
