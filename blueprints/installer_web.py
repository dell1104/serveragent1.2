# installer_web.py - Servidor de Instaladores Web

from flask import Blueprint, send_file, jsonify, request, abort
import os
import json
from datetime import datetime
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Blueprint para servir instaladores web
installer_web_bp = Blueprint('installer_web', __name__, url_prefix='/api/installer-web')

# Directorio de instaladores generados
GENERATED_INSTALLERS_DIR = 'instaladores'
INSTALLERS_DIST_DIR = 'instaladores'

# Crear directorios si no existen
os.makedirs(GENERATED_INSTALLERS_DIR, exist_ok=True)
os.makedirs(INSTALLERS_DIST_DIR, exist_ok=True)

@installer_web_bp.route('/list', methods=['GET'])
def list_installers():
    """Lista todos los instaladores disponibles"""
    try:
        installers = []
        
        # Leer configuración de instaladores
        config_path = os.path.join(GENERATED_INSTALLERS_DIR, 'installers.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                installers = config.get('installers', [])
        else:
            # Configuración por defecto
            installers = [
                {
                    "os": "windows",
                    "arch": "x64",
                    "name": "Windows 64-bit",
                    "filename": "ForensicAgent-Windows-Installer.exe",
                    "type": "exe",
                    "size": "0",
                    "description": "Instalador ejecutable para Windows 10/11 (64-bit)"
                },
                {
                    "os": "windows",
                    "arch": "x64",
                    "name": "Windows 64-bit MSI",
                    "filename": "ForensicAgent-Windows-Installer.msi",
                    "type": "msi",
                    "size": "0",
                    "description": "Instalador MSI para Windows 10/11 (64-bit)"
                },
                {
                    "os": "linux",
                    "arch": "x64",
                    "name": "Linux 64-bit",
                    "filename": "ForensicAgent-Linux-Installer.deb",
                    "type": "deb",
                    "size": "0",
                    "description": "Instalador DEB para Ubuntu/Debian (64-bit)"
                },
                {
                    "os": "macos",
                    "arch": "x64",
                    "name": "macOS Intel",
                    "filename": "ForensicAgent-Mac-Installer.dmg",
                    "type": "dmg",
                    "size": "0",
                    "description": "Instalador DMG para macOS Intel"
                }
            ]
        
        # Verificar qué archivos existen realmente
        available_installers = []
        for installer in installers:
            file_path = os.path.join(INSTALLERS_DIST_DIR, installer['filename'])
            if os.path.exists(file_path):
                # Obtener tamaño real del archivo
                installer['size'] = str(os.path.getsize(file_path))
                installer['available'] = True
                available_installers.append(installer)
            else:
                installer['available'] = False
                available_installers.append(installer)
        
        return jsonify({
            'status': 'success',
            'installers': available_installers,
            'count': len(available_installers),
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error listando instaladores: {e}")
        return jsonify({'error': str(e)}), 500

@installer_web_bp.route('/download/<filename>', methods=['GET'])
def download_installer(filename):
    """Descarga un instalador específico"""
    try:
        # Validar nombre de archivo
        if not filename or '..' in filename or '/' in filename or '\\' in filename:
            abort(400, "Nombre de archivo inválido")
        
        # Ruta del archivo
        file_path = os.path.join(INSTALLERS_DIST_DIR, filename)
        
        # Verificar que el archivo existe
        if not os.path.exists(file_path):
            abort(404, "Instalador no encontrado")
        
        # Obtener información del archivo
        file_size = os.path.getsize(file_path)
        
        # Log de descarga
        logger.info(f"Descarga de instalador: {filename} ({file_size} bytes)")
        
        # Enviar archivo
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Error descargando instalador {filename}: {e}")
        return jsonify({'error': str(e)}), 500

@installer_web_bp.route('/detect', methods=['GET'])
def detect_system():
    """Detecta el sistema operativo del cliente"""
    try:
        user_agent = request.headers.get('User-Agent', '').lower()
        platform = request.headers.get('Sec-Ch-Ua-Platform', '').lower()
        
        # Detectar sistema operativo
        if 'windows' in user_agent:
            os_type = 'windows'
            os_name = 'Microsoft Windows'
            os_icon = '🪟'
        elif 'mac' in user_agent or 'macos' in user_agent:
            os_type = 'macos'
            os_name = 'macOS'
            os_icon = '🍎'
        elif 'linux' in user_agent or 'x11' in user_agent:
            os_type = 'linux'
            os_name = 'Linux'
            os_icon = '🐧'
        else:
            os_type = 'unknown'
            os_name = 'Sistema Operativo Desconocido'
            os_icon = '❓'
        
        # Detectar arquitectura
        if 'x64' in user_agent or 'amd64' in user_agent:
            arch = 'x64'
        elif 'arm64' in user_agent or 'aarch64' in user_agent:
            arch = 'arm64'
        elif 'x86' in user_agent or 'i386' in user_agent:
            arch = 'x86'
        else:
            arch = 'x64'  # Por defecto
        
        # Buscar instalador recomendado
        recommended_installer = None
        config_path = os.path.join(GENERATED_INSTALLERS_DIR, 'installers.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                installers = config.get('installers', [])
                
                # Buscar el mejor match
                for installer in installers:
                    if (installer['os'] == os_type and 
                        installer['arch'] == arch and 
                        installer.get('available', True)):
                        recommended_installer = installer
                        break
                
                # Si no hay match exacto, buscar por SO
                if not recommended_installer:
                    for installer in installers:
                        if (installer['os'] == os_type and 
                            installer.get('available', True)):
                            recommended_installer = installer
                            break
        
        return jsonify({
            'status': 'success',
            'system': {
                'os': os_type,
                'os_name': os_name,
                'os_icon': os_icon,
                'arch': arch,
                'user_agent': user_agent
            },
            'recommended_installer': recommended_installer,
            'detected_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error detectando sistema: {e}")
        return jsonify({'error': str(e)}), 500

@installer_web_bp.route('/status', methods=['GET'])
def installer_status():
    """Estado de los instaladores disponibles"""
    try:
        status = {
            'windows': {'exe': False, 'msi': False},
            'linux': {'deb': False},
            'macos': {'dmg': False}
        }
        
        # Verificar archivos disponibles
        for filename in os.listdir(INSTALLERS_DIST_DIR):
            if filename.endswith('.exe'):
                status['windows']['exe'] = True
            elif filename.endswith('.msi'):
                status['windows']['msi'] = True
            elif filename.endswith('.deb'):
                status['linux']['deb'] = True
            elif filename.endswith('.dmg'):
                status['macos']['dmg'] = True
        
        # Contar archivos totales
        total_files = sum([
            status['windows']['exe'],
            status['windows']['msi'],
            status['linux']['deb'],
            status['macos']['dmg']
        ])
        
        return jsonify({
            'status': 'success',
            'installers_status': status,
            'total_available': total_files,
            'last_checked': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error verificando estado: {e}")
        return jsonify({'error': str(e)}), 500

@installer_web_bp.route('/info/<filename>', methods=['GET'])
def installer_info(filename):
    """Información detallada de un instalador"""
    try:
        # Validar nombre de archivo
        if not filename or '..' in filename or '/' in filename or '\\' in filename:
            abort(400, "Nombre de archivo inválido")
        
        # Ruta del archivo
        file_path = os.path.join(INSTALLERS_DIST_DIR, filename)
        
        # Verificar que el archivo existe
        if not os.path.exists(file_path):
            abort(404, "Instalador no encontrado")
        
        # Obtener información del archivo
        file_size = os.path.getsize(file_path)
        file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
        
        # Buscar en configuración
        installer_info = None
        config_path = os.path.join(GENERATED_INSTALLERS_DIR, 'installers.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for installer in config.get('installers', []):
                    if installer['filename'] == filename:
                        installer_info = installer
                        break
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'size': file_size,
            'size_mb': round(file_size / (1024 * 1024), 2),
            'modified': file_modified.isoformat(),
            'info': installer_info,
            'download_url': f'/api/installer-web/download/{filename}'
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo información de {filename}: {e}")
        return jsonify({'error': str(e)}), 500
