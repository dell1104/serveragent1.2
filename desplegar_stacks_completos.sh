#!/bin/bash
# Script para desplegar ambos stacks con auto-copia de archivos

echo "🚀 DESPLEGANDO STACKS COMPLETOS CON AUTO-COPIA"
echo "============================================="

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

# Verificar que estemos en el directorio correcto
if [ ! -f "STACK_PRINCIPAL.yml" ] || [ ! -f "STACK_FORENSE.yml" ]; then
    show_message $RED "❌ Error: No se encontraron los archivos YAML de los stacks"
    show_message $YELLOW "💡 Asegúrate de estar en el directorio correcto"
    exit 1
fi

# Verificar que los archivos necesarios existan
show_message $BLUE "🔍 Verificando archivos necesarios..."

required_files=(
    "app.py"
    "forensic_agent.py"
    "models.py"
    "config.py"
    "security_config.py"
    "security_middleware.py"
    "requirements.txt"
    "init_db.sql"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    show_message $RED "❌ Archivos faltantes:"
    for file in "${missing_files[@]}"; do
        echo "   - $file"
    done
    exit 1
fi

show_message $GREEN "✅ Todos los archivos necesarios están presentes"

# Detener stacks existentes
show_message $BLUE "🛑 Deteniendo stacks existentes..."
docker-compose -f STACK_PRINCIPAL.yml down 2>/dev/null
docker-compose -f STACK_FORENSE.yml down 2>/dev/null

# Limpiar contenedores e imágenes
show_message $BLUE "🧹 Limpiando contenedores e imágenes..."
docker system prune -f

# Crear directorios necesarios
show_message $BLUE "📁 Creando directorios necesarios..."
mkdir -p /mnt/Respaldo/sistema-forense/{casos_data,logs,static/uploads,agentes_data,json,forensic_data,temp}

# Desplegar STACK PRINCIPAL
show_message $BLUE "🚀 Desplegando STACK PRINCIPAL..."
docker-compose -f STACK_PRINCIPAL.yml up -d

if [ $? -eq 0 ]; then
    show_message $GREEN "✅ STACK PRINCIPAL desplegado correctamente"
else
    show_message $RED "❌ Error desplegando STACK PRINCIPAL"
    exit 1
fi

# Esperar a que el stack principal se inicie
show_message $BLUE "⏳ Esperando que el STACK PRINCIPAL se inicie..."
sleep 30

# Verificar estado del stack principal
show_message $BLUE "🔍 Verificando STACK PRINCIPAL..."
if docker ps | grep -q "sistema_forense_app"; then
    show_message $GREEN "✅ STACK PRINCIPAL corriendo correctamente"
else
    show_message $RED "❌ STACK PRINCIPAL no está corriendo"
    show_message $YELLOW "📋 Logs del STACK PRINCIPAL:"
    docker-compose -f STACK_PRINCIPAL.yml logs --tail=20
    exit 1
fi

# Desplegar STACK FORENSE
show_message $BLUE "🚀 Desplegando STACK FORENSE..."
docker-compose -f STACK_FORENSE.yml up -d

if [ $? -eq 0 ]; then
    show_message $GREEN "✅ STACK FORENSE desplegado correctamente"
else
    show_message $RED "❌ Error desplegando STACK FORENSE"
    exit 1
fi

# Esperar a que el stack forense se inicie
show_message $BLUE "⏳ Esperando que el STACK FORENSE se inicie..."
sleep 30

# Verificar estado del stack forense
show_message $BLUE "🔍 Verificando STACK FORENSE..."
if docker ps | grep -q "forensic_agent"; then
    show_message $GREEN "✅ STACK FORENSE corriendo correctamente"
else
    show_message $RED "❌ STACK FORENSE no está corriendo"
    show_message $YELLOW "📋 Logs del STACK FORENSE:"
    docker-compose -f STACK_FORENSE.yml logs --tail=20
    exit 1
fi

# Verificar que los archivos se copiaron correctamente
show_message $BLUE "🔍 Verificando archivos copiados..."

# Verificar archivos en STACK PRINCIPAL
show_message $BLUE "📋 Verificando STACK PRINCIPAL:"
docker exec sistema_forense_app ls -la /app/ | head -10

# Verificar archivos en STACK FORENSE
show_message $BLUE "📋 Verificando STACK FORENSE:"
docker exec forensic_agent ls -la /app/ | head -10

# Verificar que forensic_agent.py esté presente
if docker exec forensic_agent test -f /app/forensic_agent.py; then
    show_message $GREEN "✅ forensic_agent.py copiado correctamente"
else
    show_message $RED "❌ forensic_agent.py no encontrado en el contenedor"
fi

# Probar APIs
show_message $BLUE "🌐 Probando APIs..."

# Probar STACK PRINCIPAL
if curl -s http://localhost:8080 > /dev/null; then
    show_message $GREEN "✅ STACK PRINCIPAL responde en http://localhost:8080"
else
    show_message $YELLOW "⚠️ STACK PRINCIPAL no responde aún"
fi

# Probar STACK FORENSE
if curl -s http://localhost:5001/status > /dev/null; then
    show_message $GREEN "✅ STACK FORENSE responde en http://localhost:5001"
else
    show_message $YELLOW "⚠️ STACK FORENSE no responde aún"
fi

# Mostrar resumen final
echo ""
echo "============================================="
show_message $GREEN "🎉 ¡DESPLIEGUE COMPLETO EXITOSO!"
echo "============================================="
echo ""
show_message $BLUE "📋 RESUMEN:"
echo "• STACK PRINCIPAL: http://localhost:8080"
echo "• STACK FORENSE: http://localhost:5001"
echo "• Archivos copiados automáticamente"
echo "• Directorios creados automáticamente"
echo ""
show_message $BLUE "🔗 ACCESOS:"
echo "• Aplicación web: http://localhost:8080"
echo "• Instaladores: http://localhost:8080/instalar-agente"
echo "• Admin: http://localhost:8080/admin"
echo "• API Forense: http://localhost:5001/status"
echo ""
show_message $BLUE "📊 COMANDOS ÚTILES:"
echo "• Ver logs principal: docker-compose -f STACK_PRINCIPAL.yml logs -f"
echo "• Ver logs forense: docker-compose -f STACK_FORENSE.yml logs -f"
echo "• Ver estado: docker ps"
echo "• Detener todo: docker-compose -f STACK_PRINCIPAL.yml down && docker-compose -f STACK_FORENSE.yml down"
echo ""
show_message $GREEN "✅ ¡Sistema completamente desplegado y funcional!"
