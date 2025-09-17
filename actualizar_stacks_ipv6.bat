@echo off
echo ========================================
echo    ACTUALIZANDO STACKS CON IPv6 DESACTIVADO
echo ========================================

echo.
echo [INFO] Subiendo archivos actualizados al servidor...

:: Subir STACK_PRINCIPAL.yml
scp STACK_PRINCIPAL.yml root@192.168.1.93:/mnt/Respaldo/sistema-forense/
if %errorlevel% neq 0 (
    echo [ERROR] Error subiendo STACK_PRINCIPAL.yml
    pause
    exit /b 1
)

:: Subir STACK_FORENSE.yml
scp STACK_FORENSE.yml root@192.168.1.93:/mnt/Respaldo/sistema-forense/
if %errorlevel% neq 0 (
    echo [ERROR] Error subiendo STACK_FORENSE.yml
    pause
    exit /b 1
)

echo [INFO] Archivos subidos correctamente.

echo.
echo [INFO] Deteniendo stacks actuales...
ssh root@192.168.1.93 "cd /mnt/Respaldo/sistema-forense && docker-compose -f STACK_PRINCIPAL.yml down"
ssh root@192.168.1.93 "cd /mnt/Respaldo/sistema-forense && docker-compose -f STACK_FORENSE.yml down"

echo.
echo [INFO] Iniciando stacks con IPv6 desactivado...
ssh root@192.168.1.93 "cd /mnt/Respaldo/sistema-forense && docker-compose -f STACK_PRINCIPAL.yml up -d"
ssh root@192.168.1.93 "cd /mnt/Respaldo/sistema-forense && docker-compose -f STACK_FORENSE.yml up -d"

echo.
echo [INFO] Verificando estado de los contenedores...
ssh root@192.168.1.93 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

echo.
echo ========================================
echo    ACTUALIZACION COMPLETADA
echo ========================================
echo.
echo Los stacks han sido actualizados con IPv6 desactivado.
echo Esto deberia solucionar el error "Connection refused".
echo.
echo Prueba acceder a: http://192.168.1.93:8080
echo.

pause
