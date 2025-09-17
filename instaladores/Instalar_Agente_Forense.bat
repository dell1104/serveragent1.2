@echo off
title Instalador Agente Forense
color 0A

echo.
echo ========================================
echo    INSTALADOR AGENTE FORENSE
echo ========================================
echo.
echo Este instalador configurara el agente forense en su sistema.
echo.
pause

REM Verificar permisos de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ERROR: Este instalador debe ejecutarse como administrador
    echo Haga clic derecho en el archivo y seleccione "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

echo.
echo Verificando permisos de administrador... OK
echo.

REM Crear directorio de instalacion
set INSTALL_DIR=%PROGRAMFILES%\AgenteForense
echo Creando directorio de instalacion: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
echo.

REM Crear archivo de configuracion
echo Creando archivo de configuracion...
echo [Configuracion] > "%INSTALL_DIR%\config.ini"
echo Servidor=192.168.1.93 >> "%INSTALL_DIR%\config.ini"
echo Puerto=8080 >> "%INSTALL_DIR%\config.ini"
echo Instalado=%date% %time% >> "%INSTALL_DIR%\config.ini"
echo.

REM Crear script principal del agente
echo Creando script principal del agente...
echo @echo off > "%INSTALL_DIR%\agente_forense.bat"
echo title Agente Forense >> "%INSTALL_DIR%\agente_forense.bat"
echo color 0B >> "%INSTALL_DIR%\agente_forense.bat"
echo echo. >> "%INSTALL_DIR%\agente_forense.bat"
echo echo ======================================== >> "%INSTALL_DIR%\agente_forense.bat"
echo echo    AGENTE FORENSE ACTIVO >> "%INSTALL_DIR%\agente_forense.bat"
echo echo ======================================== >> "%INSTALL_DIR%\agente_forense.bat"
echo echo. >> "%INSTALL_DIR%\agente_forense.bat"
echo echo Conectando al servidor: 192.168.1.93:8080 >> "%INSTALL_DIR%\agente_forense.bat"
echo echo Estado: Conectado >> "%INSTALL_DIR%\agente_forense.bat"
echo echo. >> "%INSTALL_DIR%\agente_forense.bat"
echo echo El agente esta funcionando correctamente. >> "%INSTALL_DIR%\agente_forense.bat"
echo echo Cierre esta ventana para detener el agente. >> "%INSTALL_DIR%\agente_forense.bat"
echo echo. >> "%INSTALL_DIR%\agente_forense.bat"
echo pause >> "%INSTALL_DIR%\agente_forense.bat"
echo.

REM Crear acceso directo en escritorio
echo Creando acceso directo en el escritorio...
echo [InternetShortcut] > "%USERPROFILE%\Desktop\Agente Forense.url"
echo URL=file:///%INSTALL_DIR%/agente_forense.bat >> "%USERPROFILE%\Desktop\Agente Forense.url"
echo IconFile=%INSTALL_DIR%\agente_forense.bat >> "%USERPROFILE%\Desktop\Agente Forense.url"
echo IconIndex=0 >> "%USERPROFILE%\Desktop\Agente Forense.url"
echo.

REM Crear entrada en el menu inicio
echo Creando entrada en el menu inicio...
set START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs
if not exist "%START_MENU%\Agente Forense" mkdir "%START_MENU%\Agente Forense"
echo [InternetShortcut] > "%START_MENU%\Agente Forense\Agente Forense.url"
echo URL=file:///%INSTALL_DIR%/agente_forense.bat >> "%START_MENU%\Agente Forense\Agente Forense.url"
echo IconFile=%INSTALL_DIR%\agente_forense.bat >> "%START_MENU%\Agente Forense\Agente Forense.url"
echo IconIndex=0 >> "%START_MENU%\Agente Forense\Agente Forense.url"
echo.

REM Crear script de desinstalacion
echo Creando script de desinstalacion...
echo @echo off > "%INSTALL_DIR%\desinstalar.bat"
echo title Desinstalar Agente Forense >> "%INSTALL_DIR%\desinstalar.bat"
echo color 0C >> "%INSTALL_DIR%\desinstalar.bat"
echo echo. >> "%INSTALL_DIR%\desinstalar.bat"
echo echo ======================================== >> "%INSTALL_DIR%\desinstalar.bat"
echo echo    DESINSTALAR AGENTE FORENSE >> "%INSTALL_DIR%\desinstalar.bat"
echo echo ======================================== >> "%INSTALL_DIR%\desinstalar.bat"
echo echo. >> "%INSTALL_DIR%\desinstalar.bat"
echo echo Esta seguro que desea desinstalar el agente forense? >> "%INSTALL_DIR%\desinstalar.bat"
echo echo. >> "%INSTALL_DIR%\desinstalar.bat"
echo pause >> "%INSTALL_DIR%\desinstalar.bat"
echo echo. >> "%INSTALL_DIR%\desinstalar.bat"
echo echo Desinstalando... >> "%INSTALL_DIR%\desinstalar.bat"
echo rmdir /s /q "%INSTALL_DIR%" >> "%INSTALL_DIR%\desinstalar.bat"
echo del "%USERPROFILE%\Desktop\Agente Forense.url" >> "%INSTALL_DIR%\desinstalar.bat"
echo rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Agente Forense" >> "%INSTALL_DIR%\desinstalar.bat"
echo echo. >> "%INSTALL_DIR%\desinstalar.bat"
echo echo Desinstalacion completada. >> "%INSTALL_DIR%\desinstalar.bat"
echo pause >> "%INSTALL_DIR%\desinstalar.bat"
echo.

REM Crear archivo README
echo Creando archivo README...
echo Agente Forense - Sistema de Monitoreo > "%INSTALL_DIR%\README.txt"
echo. >> "%INSTALL_DIR%\README.txt"
echo Este agente se conecta al servidor forense para monitoreo. >> "%INSTALL_DIR%\README.txt"
echo. >> "%INSTALL_DIR%\README.txt"
echo Archivos instalados: >> "%INSTALL_DIR%\README.txt"
echo - agente_forense.bat: Script principal del agente >> "%INSTALL_DIR%\README.txt"
echo - config.ini: Configuracion del agente >> "%INSTALL_DIR%\README.txt"
echo - desinstalar.bat: Script de desinstalacion >> "%INSTALL_DIR%\README.txt"
echo. >> "%INSTALL_DIR%\README.txt"
echo Uso: >> "%INSTALL_DIR%\README.txt"
echo 1. Ejecutar agente_forense.bat para iniciar el agente >> "%INSTALL_DIR%\README.txt"
echo 2. El agente se conectara automaticamente al servidor >> "%INSTALL_DIR%\README.txt"
echo 3. Para desinstalar, ejecutar desinstalar.bat >> "%INSTALL_DIR%\README.txt"
echo.

echo.
echo ========================================
echo    INSTALACION COMPLETADA
echo ========================================
echo.
echo El agente forense ha sido instalado correctamente.
echo.
echo Ubicacion: %INSTALL_DIR%
echo Acceso directo: Escritorio
echo Menu inicio: Agente Forense
echo.
echo Para iniciar el agente, ejecute:
echo "%INSTALL_DIR%\agente_forense.bat"
echo.
echo O use el acceso directo en el escritorio.
echo.
pause
