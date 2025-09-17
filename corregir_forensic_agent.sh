#!/bin/bash
# Script para corregir rápidamente el problema del forensic_agent

echo "🔧 CORRIGIENDO FORENSIC_AGENT"
echo "============================="

# Verificar que el contenedor esté corriendo
if ! docker ps | grep -q "forensic_agent"; then
    echo "❌ Contenedor forensic_agent no está corriendo"
    echo "💡 Ejecuta: docker-compose -f STACK_FORENSE.yml up -d"
    exit 1
fi

echo "✅ Contenedor forensic_agent encontrado"

# Copiar el archivo manualmente
echo "📋 Copiando forensic_agent.py al contenedor..."
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

# Hacer el archivo ejecutable
echo "🔧 Haciendo el archivo ejecutable..."
docker exec forensic_agent chmod +x /app/forensic_agent.py

# Reiniciar el contenedor
echo "🔄 Reiniciando contenedor..."
docker restart forensic_agent

if [ $? -eq 0 ]; then
    echo "✅ Contenedor reiniciado correctamente"
else
    echo "❌ Error reiniciando contenedor"
    exit 1
fi

# Esperar a que se inicie
echo "⏳ Esperando que el contenedor se inicie..."
sleep 15

# Verificar logs
echo "📋 Logs del contenedor:"
docker logs forensic_agent --tail=10

# Probar la API
echo "🌐 Probando API del agente:"
curl -s http://localhost:5001/status 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ API del agente responde correctamente"
else
    echo "⚠️ API del agente no responde aún"
fi

echo ""
echo "🎉 ¡CORRECCIÓN COMPLETADA!"
echo "========================="
