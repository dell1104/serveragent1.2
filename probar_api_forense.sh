#!/bin/bash

echo "=== PROBANDO API DEL AGENTE FORENSE ==="

# Verificar que el agente esté ejecutándose
echo "1. Verificando estado del agente..."
docker exec forensic_agent ps aux | grep python

echo ""
echo "2. Probando endpoint de salud..."
docker exec forensic_agent curl -s http://localhost:5001/health

echo ""
echo "3. Probando endpoint de información del agente..."
docker exec forensic_agent curl -s http://localhost:5001/agent/info

echo ""
echo "4. Probando endpoint de capacidades..."
docker exec forensic_agent curl -s http://localhost:5001/agent/capabilities

echo ""
echo "5. Probando endpoint de estado del sistema..."
docker exec forensic_agent curl -s http://localhost:5001/system/status

echo ""
echo "6. Verificando que el agente puede comunicarse con el stack principal..."
docker exec forensic_agent curl -s http://sistema-forense-app:5000/ || echo "No se puede conectar al stack principal"

echo ""
echo "=== PRUEBAS COMPLETADAS ==="
