@echo off
setlocal enabledelayedexpansion

:: Verificar permisos de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Este instalador requiere permisos de administrador
    echo Ejecuta como administrador y vuelve a intentar
    pause
    exit /b 1
)

echo ========================================
echo    INSTALADOR AGENTE FORENSE WINDOWS
echo ========================================
echo.

:: Obtener parámetros
set USER_ID=%1
set SERVER_URL=%2
set TOKEN=%3

if "%USER_ID%"=="" (
    echo ERROR: Falta el ID de usuario
    echo Uso: instalador_windows.bat USER_ID SERVER_URL TOKEN
    pause
    exit /b 1
)

if "%SERVER_URL%"=="" (
    echo ERROR: Falta la URL del servidor
    echo Uso: instalador_windows.bat USER_ID SERVER_URL TOKEN
    pause
    exit /b 1
)

if "%TOKEN%"=="" (
    echo ERROR: Falta el token de registro
    echo Uso: instalador_windows.bat USER_ID SERVER_URL TOKEN
    pause
    exit /b 1
)

echo Usuario: %USER_ID%
echo Servidor: %SERVER_URL%
echo Token: %TOKEN%
echo.

:: Crear directorio de instalacion
set INSTALL_DIR=C:\Program Files\SistemaForenseAgente
echo [INFO] Creando directorio: %INSTALL_DIR%
mkdir "%INSTALL_DIR%" 2>nul

:: Verificar Python
echo [INFO] Verificando Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python no esta instalado
    echo Por favor instala Python 3.7+ desde https://python.org
    echo.
    echo ¿Deseas abrir la página de descarga de Python? (S/N)
    set /p choice=
    if /i "%choice%"=="S" (
        start https://www.python.org/downloads/
    )
    pause
    exit /b 1
)

echo [INFO] Python encontrado
python --version

:: Instalar dependencias
echo [INFO] Instalando dependencias Python...
cd /d "%INSTALL_DIR%"
pip install flask==2.3.3 flask-cors==4.0.0 psutil==5.9.6 wmi==1.5.1 requests==2.31.0

:: Crear script de inicio
echo [INFO] Creando script de inicio...
(
echo @echo off
echo cd /d "%INSTALL_DIR%"
echo python agente_windows_parametrizado.py --server_url "%SERVER_URL%" --token "%TOKEN%"
echo pause
) > "%INSTALL_DIR%\iniciar_agente.bat"

:: Crear acceso directo en el escritorio
echo [INFO] Creando acceso directo...
set DESKTOP=%USERPROFILE%\Desktop
(
echo [InternetShortcut]
echo URL=http://127.0.0.1:5001
echo IconFile=%INSTALL_DIR%\iniciar_agente.bat
echo IconIndex=0
) > "%DESKTOP%\Agente Forense.url"

:: Crear entrada en el menu inicio
echo [INFO] Creando entrada en el menu inicio...
set START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs
mkdir "%START_MENU%\Sistema Forense" 2>nul
copy "%INSTALL_DIR%\iniciar_agente.bat" "%START_MENU%\Sistema Forense\"

:: Configurar firewall
echo [INFO] Configurando firewall...
netsh advfirewall firewall add rule name="Agente Forense" dir=in action=allow protocol=TCP localport=5001

echo.
echo ========================================
echo    INSTALACION COMPLETADA
echo ========================================
echo.
echo El agente forense ha sido instalado en:
echo %INSTALL_DIR%
echo.
echo Para iniciar el agente:
echo 1. Ejecuta "iniciar_agente.bat" desde el escritorio
echo 2. O ve a Menu Inicio ^> Sistema Forense
echo.
echo El agente estara disponible en: http://127.0.0.1:5001
echo.
echo ¿Deseas iniciar el agente ahora? (S/N)
set /p choice=
if /i "%choice%"=="S" (
    start "" "%INSTALL_DIR%\iniciar_agente.bat"
)
pause
