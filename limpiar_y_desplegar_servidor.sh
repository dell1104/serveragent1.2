#!/bin/bash
# Script de limpieza y despliegue completo para el servidor

echo "🧹 INICIANDO LIMPIEZA Y DESPLIEGUE COMPLETO"
echo "=========================================="

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

# PASO 1: Detener contenedores
show_message $BLUE "🛑 PASO 1: Deteniendo contenedores existentes..."
docker-compose down
if [ $? -eq 0 ]; then
    show_message $GREEN "✅ Contenedores detenidos correctamente"
else
    show_message $YELLOW "⚠️  No había contenedores corriendo o error al detener"
fi

# PASO 2: Eliminar contenedores
show_message $BLUE "🗑️ PASO 2: Eliminando contenedores..."
docker-compose rm -f
if [ $? -eq 0 ]; then
    show_message $GREEN "✅ Contenedores eliminados correctamente"
else
    show_message $YELLOW "⚠️  No había contenedores para eliminar"
fi

# PASO 3: Eliminar imágenes
show_message $BLUE "🖼️ PASO 3: Eliminando imágenes del sistema forense..."
docker rmi sistema-forense-main_app sistema-forense-main_redis 2>/dev/null
if [ $? -eq 0 ]; then
    show_message $GREEN "✅ Imágenes eliminadas correctamente"
else
    show_message $YELLOW "⚠️  No había imágenes para eliminar"
fi

# PASO 4: Limpiar volúmenes
show_message $BLUE "📦 PASO 4: Limpiando volúmenes..."
docker volume prune -f
if [ $? -eq 0 ]; then
    show_message $GREEN "✅ Volúmenes limpiados correctamente"
else
    show_message $YELLOW "⚠️  No había volúmenes para limpiar"
fi

# PASO 5: Limpiar redes
show_message $BLUE "🌐 PASO 5: Limpiando redes..."
docker network prune -f
if [ $? -eq 0 ]; then
    show_message $GREEN "✅ Redes limpiadas correctamente"
else
    show_message $YELLOW "⚠️  No había redes para limpiar"
fi

# PASO 6: Verificar que no queden contenedores
show_message $BLUE "🔍 PASO 6: Verificando limpieza..."
CONTAINERS=$(docker ps -a --filter "name=sistema-forense" --format "{{.Names}}")
if [ -z "$CONTAINERS" ]; then
    show_message $GREEN "✅ No quedan contenedores del sistema forense"
else
    show_message $RED "❌ Aún quedan contenedores: $CONTAINERS"
    show_message $YELLOW "💡 Eliminando contenedores restantes..."
    docker rm -f $CONTAINERS
fi

# PASO 7: Reconstruir imágenes
show_message $BLUE "🔨 PASO 7: Reconstruyendo imágenes..."
docker-compose build --no-cache
if [ $? -eq 0 ]; then
    show_message $GREEN "✅ Imágenes reconstruidas correctamente"
else
    show_message $RED "❌ Error al reconstruir imágenes"
    exit 1
fi

# PASO 8: Iniciar servicios
show_message $BLUE "🚀 PASO 8: Iniciando servicios..."
docker-compose up -d
if [ $? -eq 0 ]; then
    show_message $GREEN "✅ Servicios iniciados correctamente"
else
    show_message $RED "❌ Error al iniciar servicios"
    exit 1
fi

# PASO 9: Verificar estado
show_message $BLUE "🔍 PASO 9: Verificando estado de los servicios..."
sleep 10

# Verificar contenedores
CONTAINERS_RUNNING=$(docker ps --filter "name=sistema-forense" --format "{{.Names}}" | wc -l)
if [ $CONTAINERS_RUNNING -gt 0 ]; then
    show_message $GREEN "✅ $CONTAINERS_RUNNING contenedores del sistema forense están corriendo"
    docker ps --filter "name=sistema-forense" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
else
    show_message $RED "❌ No hay contenedores del sistema forense corriendo"
fi

# Verificar logs
show_message $BLUE "📋 PASO 10: Mostrando logs de inicio..."
echo "=== LOGS DE LA APLICACIÓN ==="
docker-compose logs --tail=20 app

echo ""
echo "=== LOGS DE REDIS ==="
docker-compose logs --tail=10 redis

# PASO 11: Verificar conectividad
show_message $BLUE "🌐 PASO 11: Verificando conectividad..."
sleep 5

# Verificar si la aplicación responde
if curl -s http://localhost:5000 > /dev/null; then
    show_message $GREEN "✅ La aplicación responde en http://localhost:5000"
else
    show_message $YELLOW "⚠️  La aplicación no responde aún, esperando..."
    sleep 10
    if curl -s http://localhost:5000 > /dev/null; then
        show_message $GREEN "✅ La aplicación ahora responde en http://localhost:5000"
    else
        show_message $RED "❌ La aplicación no responde después de 15 segundos"
    fi
fi

# RESUMEN FINAL
echo ""
echo "=========================================="
show_message $GREEN "🎉 DESPLIEGUE COMPLETO FINALIZADO"
echo "=========================================="
echo ""
show_message $BLUE "📋 RESUMEN:"
echo "• Contenedores detenidos y eliminados"
echo "• Imágenes reconstruidas desde cero"
echo "• Volúmenes y redes limpiados"
echo "• Servicios iniciados con configuración fresca"
echo ""
show_message $BLUE "🔗 ACCESOS:"
echo "• Aplicación: http://localhost:5000"
echo "• Instaladores: http://localhost:5000/instalar-agente"
echo "• Admin: http://localhost:5000/admin"
echo ""
show_message $BLUE "📊 COMANDOS ÚTILES:"
echo "• Ver logs: docker-compose logs -f"
echo "• Ver estado: docker-compose ps"
echo "• Detener: docker-compose down"
echo "• Reiniciar: docker-compose restart"
echo ""
show_message $GREEN "✅ ¡Sistema completamente desplegado y listo para usar!"
