#!/usr/bin/env python3
"""
Blueprint para generar instaladores de agente dinámicamente
"""

from flask import Blueprint, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
import os
import uuid
import tempfile
import subprocess
import shutil
from pathlib import Path

installer_agente_bp = Blueprint('installer_agente', __name__)

@installer_agente_bp.route('/api/installer-agente/generate', methods=['POST'])
@login_required
def generate_agent_installer():
    """Genera un instalador de agente personalizado"""
    try:
        data = request.json
        user_id = current_user.id
        server_url = request.host_url.strip('/')
        
        # Generar token único
        token = str(uuid.uuid4())
        
        # Crear directorio temporal
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Generando instalador en: {temp_dir}")
            
            # Crear estructura de directorios
            install_dir = os.path.join(temp_dir, 'instalador')
            os.makedirs(install_dir, exist_ok=True)
            
            # Copiar agente
            agente_path = os.path.join(current_app.root_path, 'agente_windows_parametrizado.py')
            if os.path.exists(agente_path):
                shutil.copy(agente_path, install_dir)
            else:
                return jsonify({
                    'success': False,
                    'error': 'Archivo del agente no encontrado'
                }), 404
            
            # Crear script de instalación
            install_script = f'''@echo off
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
echo    INSTALADOR AGENTE FORENSE
echo    Usuario: {user_id}
echo ========================================
echo.

:: Crear directorio de instalacion
set INSTALL_DIR=C:\\Program Files\\SistemaForenseAgente
echo [INFO] Creando directorio: %INSTALL_DIR%
mkdir "%INSTALL_DIR%" 2>nul

:: Copiar archivos
echo [INFO] Copiando archivos del agente...
copy "agente_windows_parametrizado.py" "%INSTALL_DIR%\\"

:: Verificar Python
echo [INFO] Verificando Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python no esta instalado
    echo Por favor instala Python 3.7+ desde https://python.org
    pause
    exit /b 1
)

:: Instalar dependencias
echo [INFO] Instalando dependencias Python...
cd /d "%INSTALL_DIR%"
pip install flask==2.3.3 flask-cors==4.0.0 psutil==5.9.6 wmi==1.5.1 requests==2.31.0

:: Crear script de inicio
echo [INFO] Creando script de inicio...
(
echo @echo off
echo cd /d "%INSTALL_DIR%"
echo python agente_windows_parametrizado.py --server_url "{server_url}" --token "{token}"
echo pause
) > "%INSTALL_DIR%\\iniciar_agente.bat"

:: Crear acceso directo en el escritorio
echo [INFO] Creando acceso directo...
set DESKTOP=%USERPROFILE%\\Desktop
(
echo [InternetShortcut]
echo URL=http://127.0.0.1:5001
echo IconFile=%INSTALL_DIR%\\iniciar_agente.bat
echo IconIndex=0
) > "%DESKTOP%\\Agente Forense.url"

:: Crear entrada en el menu inicio
echo [INFO] Creando entrada en el menu inicio...
set START_MENU=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs
mkdir "%START_MENU%\\Sistema Forense" 2>nul
copy "%INSTALL_DIR%\\iniciar_agente.bat" "%START_MENU%\\Sistema Forense\\"

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
    start "" "%INSTALL_DIR%\\iniciar_agente.bat"
)
pause
'''
            
            # Guardar script de instalación
            install_path = os.path.join(install_dir, 'Instalar_Agente_Forense.bat')
            with open(install_path, 'w', encoding='utf-8') as f:
                f.write(install_script)
            
            # Crear ZIP del instalador
            zip_path = os.path.join(temp_dir, f'Instalador_Agente_Forense_{user_id}.zip')
            shutil.make_archive(zip_path.replace('.zip', ''), 'zip', install_dir)
            
            # Enviar archivo
            return send_file(
                zip_path,
                as_attachment=True,
                download_name=f'Instalador_Agente_Forense_{user_id}.zip',
                mimetype='application/zip'
            )
            
    except Exception as e:
        current_app.logger.error(f"Error generando instalador: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@installer_agente_bp.route('/api/installer-agente/generate-exe', methods=['POST'])
@login_required
def generate_agent_installer_exe():
    """Genera un instalador EXE personalizado"""
    try:
        data = request.json
        user_id = current_user.id
        server_url = request.host_url.strip('/')
        
        # Generar token único
        token = str(uuid.uuid4())
        
        # Crear directorio temporal
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Generando instalador EXE en: {temp_dir}")
            
            # Crear estructura de directorios
            install_dir = os.path.join(temp_dir, 'instalador')
            os.makedirs(install_dir, exist_ok=True)
            
            # Copiar agente
            agente_path = os.path.join(current_app.root_path, 'agente_windows_parametrizado.py')
            if os.path.exists(agente_path):
                shutil.copy(agente_path, install_dir)
            else:
                return jsonify({
                    'success': False,
                    'error': 'Archivo del agente no encontrado'
                }), 404
            
            # Crear script de instalación Python
            install_script = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instalador de Agente Forense
"""

import os
import sys
import subprocess
import ctypes
import tempfile
import shutil
from pathlib import Path

def is_admin():
    """Verifica si se ejecuta como administrador"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def mostrar_error(mensaje):
    """Muestra un popup de error"""
    ctypes.windll.user32.MessageBoxW(0, mensaje, "Error - Instalador", 0x10 | 0x0)

def mostrar_info(mensaje):
    """Muestra un popup de información"""
    ctypes.windll.user32.MessageBoxW(0, mensaje, "Instalador", 0x40 | 0x0)

def verificar_python():
    """Verifica si Python está instalado"""
    try:
        result = subprocess.run([sys.executable, '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, "Python no encontrado"
    except Exception as e:
        return False, str(e)

def instalar_dependencias():
    """Instala las dependencias necesarias"""
    dependencias = [
        'flask==2.3.3',
        'flask-cors==4.0.0',
        'psutil==5.9.6',
        'wmi==1.5.1',
        'requests==2.31.0'
    ]
    
    print("Instalando dependencias...")
    for dep in dependencias:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', dep], 
                         check=True, capture_output=True)
            print(f"✓ {dep}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Error instalando {dep}: {e}")
            return False
    return True

def crear_acceso_directo():
    """Crea acceso directo en el escritorio"""
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        path = os.path.join(desktop, "Agente Forense.lnk")
        target = r"C:\\Program Files\\SistemaForenseAgente\\iniciar_agente.bat"
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = r"C:\\Program Files\\SistemaForenseAgente"
        shortcut.IconLocation = target
        shortcut.save()
        
        return True
    except Exception as e:
        print(f"Error creando acceso directo: {e}")
        return False

def main():
    # Variables del instalador
    user_id = "{user_id}"
    server_url = "{server_url}"
    
    print("=== INSTALADOR AGENTE FORENSE ===")
    print(f"Usuario: {user_id}")
    print(f"Servidor: {server_url}")
    print()
    
    # Verificar permisos de administrador
    if not is_admin():
        mostrar_error("Este instalador requiere permisos de administrador.\\nEjecuta como administrador y vuelve a intentar.")
        sys.exit(1)
    
    # Verificar Python
    python_ok, python_version = verificar_python()
    if not python_ok:
        error_msg = f"Python no está instalado o no es compatible.\\nSe requiere Python 3.7+\\n\\nError: {python_version}"
        mostrar_error(error_msg)
        sys.exit(1)
    
    print(f"✓ Python encontrado: {python_version}")
    
    # Crear directorio de instalación
    install_dir = r"C:\\Program Files\\SistemaForenseAgente"
    try:
        os.makedirs(install_dir, exist_ok=True)
        print(f"✓ Directorio creado: {install_dir}")
    except Exception as e:
        mostrar_error(f"No se pudo crear el directorio de instalación: {e}")
        sys.exit(1)
    
    # Copiar archivos
    try:
        shutil.copy('agente_windows_parametrizado.py', install_dir)
        print("✓ Archivos copiados")
    except Exception as e:
        mostrar_error(f"Error copiando archivos: {e}")
        sys.exit(1)
    
    # Instalar dependencias
    if not instalar_dependencias():
        mostrar_error("Error instalando dependencias. Verifica tu conexión a internet.")
        sys.exit(1)
    
    # Crear script de inicio
    start_script = f"""@echo off
cd /d "{install_dir}"
python agente_windows_parametrizado.py --server_url "{server_url}" --token "{token}"
pause
"""
    
    start_path = os.path.join(install_dir, 'iniciar_agente.bat')
    with open(start_path, 'w', encoding='utf-8') as f:
        f.write(start_script)
    
    print("✓ Script de inicio creado")
    
    # Crear acceso directo
    if crear_acceso_directo():
        print("✓ Acceso directo creado en el escritorio")
    else:
        print("⚠ No se pudo crear acceso directo")
    
    # Configurar firewall
    try:
        subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule', 
                       'name=Agente Forense', 'dir=in', 'action=allow', 
                       'protocol=TCP', 'localport=5001'], 
                      check=True, capture_output=True)
        print("✓ Firewall configurado")
    except subprocess.CalledProcessError:
        print("⚠ No se pudo configurar firewall")
    
    # Mostrar mensaje de éxito
    mostrar_info(f"Instalación completada exitosamente!\\n\\nEl agente ha sido instalado en:\\n{install_dir}\\n\\nPara iniciar el agente, ejecuta el acceso directo en el escritorio.")
    
    # Preguntar si iniciar ahora
    choice = input("¿Deseas iniciar el agente ahora? (S/N): ")
    if choice.upper() == 'S':
        try:
            subprocess.Popen([start_path], shell=True)
            print("✓ Agente iniciado")
        except Exception as e:
            print(f"Error iniciando agente: {e}")

if __name__ == "__main__":
    main()
'''
            
            # Guardar script de instalación
            install_path = os.path.join(install_dir, 'instalador.py')
            with open(install_path, 'w', encoding='utf-8') as f:
                f.write(install_script)
            
            # Verificar que el script se puede ejecutar sin errores de sintaxis
            try:
                compile(install_script, install_path, 'exec')
                print("✓ Script de instalación validado")
            except SyntaxError as e:
                return jsonify({
                    'success': False,
                    'error': f'Error de sintaxis en el script generado: {e}'
                }), 500
            
            # Verificar si PyInstaller está disponible
            try:
                subprocess.run(['python', '-m', 'PyInstaller', '--version'], 
                             check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError:
                return jsonify({
                    'success': False,
                    'error': 'PyInstaller no está instalado en el servidor. Contacta al administrador.'
                }), 500
            
            # Compilar con PyInstaller
            try:
                cmd = [
                    'python', '-m', 'PyInstaller',
                    '--onefile',
                    '--windowed',
                    '--name', f'Instalador_Agente_Forense_{user_id}',
                    '--distpath', temp_dir,
                    install_path
                ]
                
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                print("✓ Instalador EXE compilado")
                
                # Buscar el archivo generado
                exe_files = list(Path(temp_dir).glob('*.exe'))
                if exe_files:
                    exe_path = exe_files[0]
                    return send_file(
                        exe_path,
                        as_attachment=True,
                        download_name=f'Instalador_Agente_Forense_{user_id}.exe',
                        mimetype='application/x-msdownload'
                    )
                else:
                    return jsonify({
                        'success': False,
                        'error': 'No se pudo generar el archivo EXE'
                    }), 500
                    
            except subprocess.CalledProcessError as e:
                # Loguea el error real y completo para ti
                error_details = e.stderr if e.stderr else e.stdout
                current_app.logger.error(f"Error al compilar con PyInstaller: {error_details}")
                
                # Devuelve un mensaje de error útil y seguro al usuario
                return jsonify({
                    'success': False,
                    'error': 'Falló la compilación del instalador en el servidor. Revisa los logs para más detalles.'
                }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error generando instalador EXE: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
