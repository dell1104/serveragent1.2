@echo off
echo ========================================
echo    INSTALADOR AGENTE FORENSE
echo ========================================
echo.
echo Instalando agente forense...
echo.

REM Crear directorio de instalación
set INSTALL_DIR=%PROGRAMFILES%\AgenteForense
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Copiar archivos (simulado)
echo Copiando archivos del agente...
timeout /t 2 /nobreak >nul

REM Crear script de inicio
echo @echo off > "%INSTALL_DIR%\iniciar_agente.bat"
echo echo Iniciando Agente Forense... >> "%INSTALL_DIR%\iniciar_agente.bat"
echo echo Agente instalado correctamente >> "%INSTALL_DIR%\iniciar_agente.bat"
echo pause >> "%INSTALL_DIR%\iniciar_agente.bat"

REM Crear acceso directo en escritorio
echo [InternetShortcut] > "%USERPROFILE%\Desktop\Agente Forense.url"
echo URL=file:///%INSTALL_DIR%/iniciar_agente.bat >> "%USERPROFILE%\Desktop\Agente Forense.url"

echo.
echo ✅ Instalación completada
echo 📁 Ubicación: %INSTALL_DIR%
echo 🖥️ Acceso directo creado en el escritorio
echo.
pause
