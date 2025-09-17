#!/bin/bash
# Script para verificar qué archivos copiaron ambos stacks

echo "🔍 VERIFICANDO COPIAS DE ARCHIVOS EN AMBOS STACKS"
echo "================================================"

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

# Verificar STACK PRINCIPAL
echo ""
show_message $BLUE "📋 VERIFICANDO STACK PRINCIPAL (sistema_forense_app):"
echo "=================================================="

if docker ps | grep -q "sistema_forense_app"; then
    show_message $GREEN "✅ Contenedor sistema_forense_app está corriendo"
    
    echo ""
    echo "📁 Contenido del directorio /app:"
    docker exec sistema_forense_app ls -la /app/ | head -15
    
    echo ""
    echo "🔍 Verificando archivos específicos:"
    echo "• app.py:"
    docker exec sistema_forense_app ls -la /app/app.py 2>/dev/null || echo "❌ No encontrado"
    
    echo "• models.py:"
    docker exec sistema_forense_app ls -la /app/models.py 2>/dev/null || echo "❌ No encontrado"
    
    echo "• blueprints/:"
    docker exec sistema_forense_app ls -la /app/blueprints/ 2>/dev/null || echo "❌ No encontrado"
    
    echo "• templates/:"
    docker exec sistema_forense_app ls -la /app/templates/ 2>/dev/null || echo "❌ No encontrado"
    
    echo "• static/:"
    docker exec sistema_forense_app ls -la /app/static/ 2>/dev/null || echo "❌ No encontrado"
    
else
    show_message $RED "❌ Contenedor sistema_forense_app no está corriendo"
fi

# Verificar STACK FORENSE
echo ""
show_message $BLUE "📋 VERIFICANDO STACK FORENSE (forensic_agent):"
echo "============================================="

if docker ps | grep -q "forensic_agent"; then
    show_message $GREEN "✅ Contenedor forensic_agent está corriendo"
    
    echo ""
    echo "📁 Contenido del directorio /app:"
    docker exec forensic_agent ls -la /app/
    
    echo ""
    echo "🔍 Verificando archivos específicos:"
    echo "• forensic_agent.py:"
    docker exec forensic_agent ls -la /app/forensic_agent.py 2>/dev/null || echo "❌ No encontrado"
    
    echo "• utils_package/:"
    docker exec forensic_agent ls -la /app/utils_package/ 2>/dev/null || echo "❌ No encontrado"
    
    echo ""
    echo "🔍 Verificando directorio /host (volumen de host):"
    docker exec forensic_agent ls -la /host/ 2>/dev/null || echo "❌ Directorio /host no encontrado"
    
    echo ""
    echo "🔍 Verificando si forensic_agent.py está en /host:"
    docker exec forensic_agent ls -la /host/forensic_agent.py 2>/dev/null || echo "❌ No encontrado en /host"
    
else
    show_message $RED "❌ Contenedor forensic_agent no está corriendo"
fi

# Verificar diferencias en la configuración de volúmenes
echo ""
show_message $BLUE "🔍 ANALIZANDO CONFIGURACIÓN DE VOLÚMENES:"
echo "============================================="

echo "📋 STACK PRINCIPAL - Volúmenes:"
echo "• /mnt/Respaldo/sistema-forense:/app"
echo "• .:/host:ro"

echo ""
echo "📋 STACK FORENSE - Volúmenes:"
echo "• /mnt/Respaldo/sistema-forense/forensic_data:/app/forensic_data"
echo "• /mnt/Respaldo/sistema-forense/logs:/app/logs"
echo "• /mnt/Respaldo/sistema-forense/temp:/app/temp"
echo "• .:/host:ro"

# Verificar si el directorio /mnt/Respaldo/sistema-forense existe
echo ""
show_message $BLUE "🔍 VERIFICANDO DIRECTORIO DE MONTAJE:"
echo "=========================================="

if [ -d "/mnt/Respaldo/sistema-forense" ]; then
    show_message $GREEN "✅ Directorio /mnt/Respaldo/sistema-forense existe"
    echo "📁 Contenido del directorio:"
    ls -la /mnt/Respaldo/sistema-forense/ | head -10
else
    show_message $RED "❌ Directorio /mnt/Respaldo/sistema-forense no existe"
    echo "💡 Esto puede ser la causa del problema"
fi

# Verificar permisos del directorio actual
echo ""
show_message $BLUE "🔍 VERIFICANDO PERMISOS DEL DIRECTORIO ACTUAL:"
echo "=================================================="

echo "📁 Directorio actual: $(pwd)"
echo "📊 Permisos:"
ls -la . | head -5

echo ""
echo "🔍 Verificando forensic_agent.py en el directorio actual:"
if [ -f "forensic_agent.py" ]; then
    show_message $GREEN "✅ forensic_agent.py existe en el directorio actual"
    ls -la forensic_agent.py
else
    show_message $RED "❌ forensic_agent.py no existe en el directorio actual"
fi

echo ""
show_message $BLUE "🎯 DIAGNÓSTICO COMPLETADO"
echo "============================="
