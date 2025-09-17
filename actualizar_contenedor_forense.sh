#!/bin/bash
# Script para actualizar el contenedor forense

echo "🔄 ACTUALIZANDO CONTENEDOR FORENSE"
echo "=================================="

# Detener el contenedor forense
echo "🛑 Deteniendo contenedor forense..."
docker-compose -f STACK_FORENSE.yml down

# Copiar archivos necesarios
echo "📁 Copiando archivos al directorio del contenedor..."

# Crear directorio si no existe
mkdir -p /mnt/Respaldo/sistema-forense

# Copiar forensic_agent.py
cp forensic_agent.py /mnt/Respaldo/sistema-forense/

if [ $? -eq 0 ]; then
    echo "✅ forensic_agent.py copiado a /mnt/Respaldo/sistema-forense/"
else
    echo "❌ Error copiando forensic_agent.py"
    exit 1
fi

# Verificar que el archivo esté en el directorio
echo "🔍 Verificando archivo..."
ls -la /mnt/Respaldo/sistema-forense/forensic_agent.py

if [ $? -eq 0 ]; then
    echo "✅ Archivo verificado"
else
    echo "❌ Archivo no encontrado"
    exit 1
fi

# Iniciar el contenedor forense
echo "🚀 Iniciando contenedor forense..."
docker-compose -f STACK_FORENSE.yml up -d

if [ $? -eq 0 ]; then
    echo "✅ Contenedor forense iniciado correctamente"
else
    echo "❌ Error iniciando contenedor forense"
    exit 1
fi

# Esperar un poco para que se inicie
echo "⏳ Esperando que el contenedor se inicie..."
sleep 10

# Verificar que esté corriendo
echo "🔍 Verificando estado del contenedor..."
docker ps | grep forensic_agent

if [ $? -eq 0 ]; then
    echo "✅ Contenedor forense corriendo correctamente"
else
    echo "❌ Contenedor forense no está corriendo"
    exit 1
fi

# Mostrar logs
echo "📋 Mostrando logs del contenedor..."
docker logs forensic_agent --tail=20

echo ""
echo "🎉 ¡CONTENEDOR FORENSE ACTUALIZADO!"
echo "=================================="
echo ""
echo "📋 PRÓXIMOS PASOS:"
echo "1. Verificar logs: docker logs forensic_agent -f"
echo "2. Probar API: curl http://localhost:5001/status"
echo "3. Verificar comunicación con stack principal"
echo ""
