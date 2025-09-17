#!/bin/bash
# Script para diagnosticar y corregir el problema del forensic_agent

echo "🔍 DIAGNOSTICANDO FORENSIC_AGENT"
echo "================================="

# Verificar que el contenedor esté corriendo
echo "📋 Verificando contenedor forensic_agent..."
if docker ps | grep -q "forensic_agent"; then
    echo "✅ Contenedor forensic_agent está corriendo"
else
    echo "❌ Contenedor forensic_agent no está corriendo"
    echo "💡 Ejecuta: docker-compose -f STACK_FORENSE.yml up -d"
    exit 1
fi

# Verificar contenido del directorio /app en el contenedor
echo ""
echo "📁 Contenido del directorio /app en el contenedor:"
docker exec forensic_agent ls -la /app/

# Verificar si forensic_agent.py existe
echo ""
echo "🔍 Verificando forensic_agent.py:"
if docker exec forensic_agent test -f /app/forensic_agent.py; then
    echo "✅ forensic_agent.py encontrado en el contenedor"
    echo "📊 Información del archivo:"
    docker exec forensic_agent ls -la /app/forensic_agent.py
else
    echo "❌ forensic_agent.py NO encontrado en el contenedor"
    echo "🔧 Intentando copiar manualmente..."
    
    # Copiar el archivo manualmente
    echo "📋 Copiando forensic_agent.py al contenedor..."
    docker cp forensic_agent.py forensic_agent:/app/forensic_agent.py
    
    if [ $? -eq 0 ]; then
        echo "✅ forensic_agent.py copiado correctamente"
        echo "📊 Verificando archivo copiado:"
        docker exec forensic_agent ls -la /app/forensic_agent.py
    else
        echo "❌ Error copiando forensic_agent.py"
        exit 1
    fi
fi

# Verificar que el archivo sea ejecutable
echo ""
echo "🔧 Verificando permisos del archivo:"
docker exec forensic_agent chmod +x /app/forensic_agent.py

# Verificar logs del contenedor
echo ""
echo "📋 Logs recientes del contenedor:"
docker logs forensic_agent --tail=20

# Reiniciar el contenedor para que use el archivo
echo ""
echo "🔄 Reiniciando contenedor para aplicar cambios..."
docker restart forensic_agent

if [ $? -eq 0 ]; then
    echo "✅ Contenedor reiniciado correctamente"
else
    echo "❌ Error reiniciando contenedor"
    exit 1
fi

# Esperar a que se inicie
echo "⏳ Esperando que el contenedor se inicie..."
sleep 10

# Verificar que esté corriendo
echo ""
echo "🔍 Verificando estado del contenedor:"
docker ps | grep forensic_agent

# Verificar logs después del reinicio
echo ""
echo "📋 Logs después del reinicio:"
docker logs forensic_agent --tail=10

# Probar la API si está disponible
echo ""
echo "🌐 Probando API del agente:"
curl -s http://localhost:5001/status 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ API del agente responde correctamente"
else
    echo "⚠️ API del agente no responde (puede estar iniciando)"
fi

echo ""
echo "🎉 ¡DIAGNÓSTICO COMPLETADO!"
echo "==========================="
