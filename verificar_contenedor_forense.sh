#!/bin/bash
# Script para verificar el contenedor forense

echo "🔍 VERIFICANDO CONTENEDOR FORENSE"
echo "================================="

# Verificar que el contenedor esté corriendo
echo "📋 Estado del contenedor:"
docker ps | grep forensic_agent

if [ $? -eq 0 ]; then
    echo "✅ Contenedor forensic_agent está corriendo"
else
    echo "❌ Contenedor forensic_agent no está corriendo"
    echo "💡 Ejecuta: docker-compose -f STACK_FORENSE.yml up -d"
    exit 1
fi

# Verificar que el archivo esté en el contenedor
echo ""
echo "📁 Verificando archivos en el contenedor:"
docker exec forensic_agent ls -la /app/

# Verificar que forensic_agent.py esté presente
echo ""
echo "🔍 Verificando forensic_agent.py:"
docker exec forensic_agent ls -la /app/forensic_agent.py

if [ $? -eq 0 ]; then
    echo "✅ forensic_agent.py encontrado en el contenedor"
else
    echo "❌ forensic_agent.py no encontrado en el contenedor"
    echo "💡 Ejecuta: ./copiar_archivos_contenedor.sh"
    exit 1
fi

# Verificar que el proceso esté corriendo
echo ""
echo "⚙️ Verificando proceso Python:"
docker exec forensic_agent ps aux | grep python

# Verificar logs recientes
echo ""
echo "📋 Logs recientes del contenedor:"
docker logs forensic_agent --tail=10

# Probar API si está disponible
echo ""
echo "🌐 Probando API del agente:"
curl -s http://localhost:5001/status 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ API del agente responde correctamente"
else
    echo "⚠️ API del agente no responde (puede estar iniciando)"
fi

echo ""
echo "🎉 ¡VERIFICACIÓN COMPLETADA!"
echo "============================"
