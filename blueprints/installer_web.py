#!/usr/bin/env python3
"""
Blueprint para el instalador web con detección automática de OS
"""

from flask import Blueprint, request, jsonify, send_file, current_app, render_template
from flask_login import login_required, current_user
import os
import uuid
import tempfile
import shutil
from pathlib import Path

installer_web_bp = Blueprint('installer_web', __name__)

@installer_web_bp.route('/instalar-agente-web')
@login_required
def instalar_agente_web():
    """Página principal del instalador web"""
    return render_template('instalador_web.html')

@installer_web_bp.route('/api/installer-web/generate-token', methods=['POST'])
@login_required
def generate_token():
    """Genera un token único para el agente"""
    try:
        token = str(uuid.uuid4())
        return jsonify({
            'success': True,
            'token': token
        })
    except Exception as e:
        current_app.logger.error(f"Error generando token: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@installer_web_bp.route('/api/installer-web/download/<os_type>/<installer_type>')
@login_required
def download_installer(os_type, installer_type):
    """Descarga el instalador correspondiente al OS y tipo"""
    try:
        # Obtener parámetros
        user_id = request.args.get('user_id', current_user.id)
        server_url = request.args.get('server_url', request.host_url.strip('/'))
        token = request.args.get('token')
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Token de registro requerido'
            }), 400
        
        # Crear directorio temporal
        with tempfile.TemporaryDirectory() as temp_dir:
            install_dir = os.path.join(temp_dir, 'instalador')
            os.makedirs(install_dir, exist_ok=True)
            
            # Copiar agente correspondiente
            agente_files = {
                'windows': 'agente_windows_parametrizado.py',
                'linux': 'agente_linux_parametrizado.py',
                'macos': 'agente_macos_parametrizado.py'
            }
            
            agente_name = agente_files.get(os_type)
            if not agente_name:
                return jsonify({
                    'success': False,
                    'error': f'Sistema operativo no soportado: {os_type}'
                }), 400
            
            # Buscar archivo del agente
            agente_path = os.path.join(current_app.root_path, agente_name)
            if not os.path.exists(agente_path):
                # Si no existe el específico, usar el genérico
                agente_path = os.path.join(current_app.root_path, 'agente_windows_parametrizado.py')
                if not os.path.exists(agente_path):
                    return jsonify({
                        'success': False,
                        'error': 'Archivo del agente no encontrado'
                    }), 404
            
            # Copiar agente
            shutil.copy(agente_path, install_dir)
            
            # Generar instalador personalizado
            installer_path = generar_instalador_personalizado(
                os_type, installer_type, install_dir, 
                user_id, server_url, token
            )
            
            if not installer_path:
                return jsonify({
                    'success': False,
                    'error': f'Tipo de instalador no soportado: {installer_type}'
                }), 400
            
            # Determinar nombre del archivo y tipo MIME
            file_info = get_file_info(os_type, installer_type)
            
            return send_file(
                installer_path,
                as_attachment=True,
                download_name=file_info['filename'],
                mimetype=file_info['mimetype']
            )
            
    except Exception as e:
        current_app.logger.error(f"Error descargando instalador: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generar_instalador_personalizado(os_type, installer_type, install_dir, user_id, server_url, token):
    """Genera un instalador personalizado con los parámetros del usuario"""
    
    if os_type == 'windows':
        if installer_type == 'bat':
            return generar_instalador_windows_bat(install_dir, user_id, server_url, token)
        elif installer_type == 'zip':
            return generar_instalador_windows_zip(install_dir, user_id, server_url, token)
    
    elif os_type == 'linux':
        if installer_type == 'sh':
            return generar_instalador_linux_sh(install_dir, user_id, server_url, token)
        elif installer_type == 'deb':
            return generar_instalador_linux_deb(install_dir, user_id, server_url, token)
    
    elif os_type == 'macos':
        if installer_type == 'sh':
            return generar_instalador_macos_sh(install_dir, user_id, server_url, token)
        elif installer_type == 'dmg':
            return generar_instalador_macos_dmg(install_dir, user_id, server_url, token)
    
    return None

def generar_instalador_windows_bat(install_dir, user_id, server_url, token):
    """Genera instalador BAT personalizado para Windows"""
    
    # Leer el instalador base
    base_installer_path = os.path.join(current_app.root_path, 'instaladores', 'windows', 'instalador_windows.bat')
    
    if not os.path.exists(base_installer_path):
        # Crear instalador básico si no existe
        installer_content = f'''@echo off
setlocal enabledelayedexpansion

echo ========================================
echo    INSTALADOR AGENTE FORENSE WINDOWS
echo ========================================
echo.
echo Usuario: {user_id}
echo Servidor: {server_url}
echo Token: {token}
echo.

:: Verificar permisos de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Este instalador requiere permisos de administrador
    echo Ejecuta como administrador y vuelve a intentar
    pause
    exit /b 1
)

:: Crear directorio de instalacion
set INSTALL_DIR=C:\\Program Files\\SistemaForenseAgente
echo [INFO] Creando directorio: %INSTALL_DIR%
mkdir "%INSTALL_DIR%" 2>nul

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

:: Crear acceso directo
echo [INFO] Creando acceso directo...
set DESKTOP=%USERPROFILE%\\Desktop
(
echo [InternetShortcut]
echo URL=http://127.0.0.1:5001
echo IconFile=%INSTALL_DIR%\\iniciar_agente.bat
echo IconIndex=0
) > "%DESKTOP%\\Agente Forense.url"

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
    else:
        # Leer y personalizar el instalador base
        with open(base_installer_path, 'r', encoding='utf-8') as f:
            installer_content = f.read()
    
    # Guardar instalador personalizado
    installer_path = os.path.join(install_dir, f'Instalador_Agente_Forense_{user_id}.bat')
    with open(installer_path, 'w', encoding='utf-8') as f:
        f.write(installer_content)
    
    return installer_path

def generar_instalador_windows_zip(install_dir, user_id, server_url, token):
    """Genera instalador ZIP para Windows"""
    # Crear ZIP con todos los archivos
    zip_path = os.path.join(install_dir, f'Instalador_Agente_Forense_{user_id}.zip')
    shutil.make_archive(zip_path.replace('.zip', ''), 'zip', install_dir)
    return zip_path

def generar_instalador_linux_sh(install_dir, user_id, server_url, token):
    """Genera instalador SH personalizado para Linux"""
    
    # Leer el instalador base
    base_installer_path = os.path.join(current_app.root_path, 'instaladores', 'linux', 'instalador_linux.sh')
    
    if not os.path.exists(base_installer_path):
        return None
    
    # Leer y personalizar el instalador base
    with open(base_installer_path, 'r', encoding='utf-8') as f:
        installer_content = f.read()
    
    # Guardar instalador personalizado
    installer_path = os.path.join(install_dir, f'instalador_agente_forense_{user_id}.sh')
    with open(installer_path, 'w', encoding='utf-8') as f:
        f.write(installer_content)
    
    # Hacer ejecutable
    os.chmod(installer_path, 0o755)
    
    return installer_path

def generar_instalador_linux_deb(install_dir, user_id, server_url, token):
    """Genera paquete DEB para Linux (placeholder)"""
    # Por ahora, devolver el SH
    return generar_instalador_linux_sh(install_dir, user_id, server_url, token)

def generar_instalador_macos_sh(install_dir, user_id, server_url, token):
    """Genera instalador SH personalizado para macOS"""
    
    # Leer el instalador base
    base_installer_path = os.path.join(current_app.root_path, 'instaladores', 'macos', 'instalador_macos.sh')
    
    if not os.path.exists(base_installer_path):
        return None
    
    # Leer y personalizar el instalador base
    with open(base_installer_path, 'r', encoding='utf-8') as f:
        installer_content = f.read()
    
    # Guardar instalador personalizado
    installer_path = os.path.join(install_dir, f'instalador_agente_forense_{user_id}.sh')
    with open(installer_path, 'w', encoding='utf-8') as f:
        f.write(installer_content)
    
    # Hacer ejecutable
    os.chmod(installer_path, 0o755)
    
    return installer_path

def generar_instalador_macos_dmg(install_dir, user_id, server_url, token):
    """Genera paquete DMG para macOS (placeholder)"""
    # Por ahora, devolver el SH
    return generar_instalador_macos_sh(install_dir, user_id, server_url, token)

def get_file_info(os_type, installer_type):
    """Obtiene información del archivo según OS y tipo"""
    
    file_info = {
        'windows': {
            'bat': {'filename': 'Instalador_Agente_Forense.bat', 'mimetype': 'application/x-msdownload'},
            'zip': {'filename': 'Instalador_Agente_Forense.zip', 'mimetype': 'application/zip'}
        },
        'linux': {
            'sh': {'filename': 'instalador_agente_forense.sh', 'mimetype': 'application/x-sh'},
            'deb': {'filename': 'agente_forense.deb', 'mimetype': 'application/vnd.debian.binary-package'}
        },
        'macos': {
            'sh': {'filename': 'instalador_agente_forense.sh', 'mimetype': 'application/x-sh'},
            'dmg': {'filename': 'Agente_Forense.dmg', 'mimetype': 'application/x-apple-diskimage'}
        }
    }
    
    return file_info.get(os_type, {}).get(installer_type, {
        'filename': 'instalador.bin',
        'mimetype': 'application/octet-stream'
    })