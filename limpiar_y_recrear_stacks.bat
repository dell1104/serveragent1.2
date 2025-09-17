@echo off
echo ========================================
echo    LIMPIANDO Y RECREANDO STACKS COMPLETOS
echo ========================================

echo.
echo [INFO] Deteniendo y eliminando stacks existentes...
ssh root@192.168.1.93 "cd /mnt/Respaldo/sistema-forense && docker-compose -f STACK_PRINCIPAL.yml down --volumes --remove-orphans"
ssh root@192.168.1.93 "cd /mnt/Respaldo/sistema-forense && docker-compose -f STACK_FORENSE.yml down --volumes --remove-orphans"

echo.
echo [INFO] Eliminando redes huérfanas...
ssh root@192.168.1.93 "docker network prune -f"

echo.
echo [INFO] Eliminando contenedores huérfanos...
ssh root@192.168.1.93 "docker container prune -f"

echo.
echo [INFO] Verificando que no queden redes del sistema forense...
ssh root@192.168.1.93 "docker network ls | grep forense"

echo.
echo [INFO] Subiendo archivos actualizados...
scp STACK_PRINCIPAL.yml root@192.168.1.93:/mnt/Respaldo/sistema-forense/
scp STACK_FORENSE.yml root@192.168.1.93:/mnt/Respaldo/sistema-forense/

echo.
echo [INFO] Creando stack principal desde cero...
ssh root@192.168.1.93 "cd /mnt/Respaldo/sistema-forense && docker-compose -f STACK_PRINCIPAL.yml up -d"

echo.
echo [INFO] Esperando 30 segundos para que se estabilice...
timeout /t 30 /nobreak

echo.
echo [INFO] Creando stack forense...
ssh root@192.168.1.93 "cd /mnt/Respaldo/sistema-forense && docker-compose -f STACK_FORENSE.yml up -d"

echo.
echo [INFO] Verificando estado final...
ssh root@192.168.1.93 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

echo.
echo [INFO] Verificando redes creadas...
ssh root@192.168.1.93 "docker network ls | grep forense"

echo.
echo ========================================
echo    RECREACION COMPLETADA
echo ========================================
echo.
echo Los stacks han sido recreados completamente.
echo Esto deberia solucionar el problema de red no encontrada.
echo.
echo Prueba acceder a: http://192.168.1.93:8080
echo.

pause
