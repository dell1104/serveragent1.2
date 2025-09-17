#!/bin/bash
# Script para copiar archivos al contenedor

echo "📁 COPIANDO ARCHIVOS AL CONTENEDOR FORENSE"
echo "=========================================="

# Verificar que el contenedor esté corriendo
if ! docker ps | grep -q "forensic_agent"; then
    echo "❌ El contenedor forensic_agent no está corriendo"
    echo "💡 Ejecuta primero: docker-compose -f STACK_FORENSE.yml up -d"
    exit 1
fi

echo "✅ Contenedor forensic_agent encontrado"

# Copiar forensic_agent.py al contenedor
echo "📋 Copiando forensic_agent.py..."
docker cp forensic_agent.py forensic_agent:/app/forensic_agent.py

if [ $? -eq 0 ]; then
    echo "✅ forensic_agent.py copiado correctamente"
else
    echo "❌ Error copiando forensic_agent.py"
    exit 1
fi

# Verificar que el archivo esté en el contenedor
echo "🔍 Verificando archivo en el contenedor..."
docker exec forensic_agent ls -la /app/forensic_agent.py

if [ $? -eq 0 ]; then
    echo "✅ Archivo verificado en el contenedor"
else
    echo "❌ Archivo no encontrado en el contenedor"
    exit 1
fi

# Reiniciar el contenedor para que use el nuevo archivo
echo "🔄 Reiniciando contenedor..."
docker restart forensic_agent

if [ $? -eq 0 ]; then
    echo "✅ Contenedor reiniciado correctamente"
else
    echo "❌ Error reiniciando contenedor"
    exit 1
fi

echo ""
echo "🎉 ¡ARCHIVOS COPIADOS Y CONTENEDOR REINICIADO!"
echo "=============================================="
echo ""
echo "📋 PRÓXIMOS PASOS:"
echo "1. Verificar logs: docker logs forensic_agent"
echo "2. Probar API: curl http://localhost:5001/status"
echo "3. Verificar comunicación con stack principal"
echo ""
