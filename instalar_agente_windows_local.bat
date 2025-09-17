@echo off
setlocal enabledelayedexpansion

echo ========================================
echo    INSTALADOR AGENTE FORENSE LOCAL
echo    Windows - Acceso a Discos Locales
echo ========================================
echo.

:: Verificar permisos de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Este script requiere permisos de administrador
    echo Ejecuta como administrador y vuelve a intentar
    pause
    exit /b 1
)

echo [INFO] Ejecutandose como administrador
echo.

:: Crear directorio de instalacion
set INSTALL_DIR=C:\Program Files\AgenteForense
echo [INFO] Creando directorio de instalacion: %INSTALL_DIR%
mkdir "%INSTALL_DIR%" 2>nul

:: Copiar archivos
echo [INFO] Copiando archivos del agente...
copy "agente_forense_windows_local.py" "%INSTALL_DIR%\"
copy "requirements_forensic.txt" "%INSTALL_DIR%\"

:: Instalar dependencias Python
echo [INFO] Instalando dependencias Python...
pip install flask flask-cors psutil wmi requests

:: Crear script de inicio
echo [INFO] Creando script de inicio...
(
echo @echo off
echo cd /d "%INSTALL_DIR%"
echo python agente_forense_windows_local.py
echo pause
) > "%INSTALL_DIR%\iniciar_agente.bat"

:: Crear acceso directo en el escritorio
echo [INFO] Creando acceso directo en el escritorio...
set DESKTOP=%USERPROFILE%\Desktop
(
echo [InternetShortcut]
echo URL=http://localhost:5001
echo IconFile=%INSTALL_DIR%\iniciar_agente.bat
echo IconIndex=0
) > "%DESKTOP%\Agente Forense Local.url"

:: Crear entrada en el menu inicio
echo [INFO] Creando entrada en el menu inicio...
set START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs
mkdir "%START_MENU%\Agente Forense" 2>nul
copy "%INSTALL_DIR%\iniciar_agente.bat" "%START_MENU%\Agente Forense\"

:: Configurar firewall (opcional)
echo [INFO] Configurando firewall...
netsh advfirewall firewall add rule name="Agente Forense Local" dir=in action=allow protocol=TCP localport=5001

echo.
echo ========================================
echo    INSTALACION COMPLETADA
echo ========================================
echo.
echo El agente forense local ha sido instalado en:
echo %INSTALL_DIR%
echo.
echo Para iniciar el agente:
echo 1. Ejecuta "iniciar_agente.bat" desde el escritorio
echo 2. O ve a Menu Inicio ^> Agente Forense
echo.
echo El agente estara disponible en: http://localhost:5001
echo.
pause
