#!/bin/bash

echo "=== VERIFICANDO COMUNICACIÓN ENTRE STACKS ==="

# Verificar contenedores activos
echo "1. Verificando contenedores activos..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "2. Verificando red forense..."
docker network ls | grep forense

echo ""
echo "3. Verificando conectividad entre stacks..."

# Verificar que el stack principal puede alcanzar al forense
echo "Probando conexión desde stack principal a forense..."
docker exec sistema-forense-app curl -s http://forensic_agent:5001/health || echo "Error: No se puede conectar al agente forense"

echo ""
echo "4. Verificando endpoints del agente forense..."
docker exec forensic_agent curl -s http://localhost:5001/health || echo "Error: Agente forense no responde"

echo ""
echo "5. Verificando logs del agente forense..."
docker logs forensic_agent --tail 10

echo ""
echo "6. Verificando logs del stack principal..."
docker logs sistema-forense-app --tail 10

echo ""
echo "=== VERIFICACIÓN COMPLETA ==="
