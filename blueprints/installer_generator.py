# installer_generator.py - Generador de Instaladores Personalizados

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import zipfile
import tempfile
import shutil
import json
from datetime import datetime
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Blueprint para generación de instaladores
installer_bp = Blueprint('installer', __name__, url_prefix='/api/installer')

# Directorio de plantillas de instaladores
INSTALLER_TEMPLATES_DIR = 'installer_templates'
GENERATED_INSTALLERS_DIR = 'generated_installers'

# Crear directorios si no existen
os.makedirs(INSTALLER_TEMPLATES_DIR, exist_ok=True)
os.makedirs(GENERATED_INSTALLERS_DIR, exist_ok=True)

# ==================== PLANTILLAS DE INSTALADORES ====================

WINDOWS_INSTALLER_TEMPLATE = '''@echo off
echo ========================================
echo   Instalador Agente Forense Windows
echo ========================================
echo.

REM Verificar si se ejecuta como administrador
net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: Este instalador requiere permisos de administrador.
    echo.
    echo Para ejecutar como administrador:
    echo 1. Hacer clic derecho en "Símbolo del sistema"
    echo 2. Seleccionar "Ejecutar como administrador"
    echo 3. Ejecutar este instalador
    echo.
    pause
    exit /b 1
)

echo ✅ Ejecutándose como administrador
echo.

REM Crear directorio de instalación
set INSTALL_DIR=C:\\Program Files\\ForensicAgent
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    echo ✅ Directorio de instalación creado: %INSTALL_DIR%
) else (
    echo ✅ Directorio de instalación ya existe: %INSTALL_DIR%
)

REM Crear directorio de evidencias
set EVIDENCE_DIR=C:\\evidencias_forenses
if not exist "%EVIDENCE_DIR%" (
    mkdir "%EVIDENCE_DIR%"
    echo ✅ Directorio de evidencias creado: %EVIDENCE_DIR%
) else (
    echo ✅ Directorio de evidencias ya existe: %EVIDENCE_DIR%
)

REM Copiar archivos del agente
echo.
echo 📁 Copiando archivos del agente...
copy "agent.py" "%INSTALL_DIR%\\agent.py" >nul
copy "requirements.txt" "%INSTALL_DIR%\\requirements.txt" >nul
copy "start_agent.bat" "%INSTALL_DIR%\\start_agent.bat" >nul
copy "configure_autostart.ps1" "%INSTALL_DIR%\\configure_autostart.ps1" >nul
copy "configure_autostart.bat" "%INSTALL_DIR%\\configure_autostart.bat" >nul
copy "uninstall_autostart.bat" "%INSTALL_DIR%\\uninstall_autostart.bat" >nul
copy "test_autostart.ps1" "%INSTALL_DIR%\\test_autostart.ps1" >nul
echo ✅ Archivos copiados correctamente

REM Instalar dependencias Python
echo.
echo 📦 Instalando dependencias Python...
cd /d "%INSTALL_DIR%"
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Error instalando dependencias Python
    echo.
    echo Soluciones posibles:
    echo 1. Ejecutar como administrador
    echo 2. Usar: pip install --user -r requirements.txt
    echo 3. Crear entorno virtual: python -m venv venv
    pause
    exit /b 1
)
echo ✅ Dependencias Python instaladas

REM Configurar inicio automático
echo.
echo 🚀 Configurando inicio automático...
powershell -ExecutionPolicy Bypass -File "%INSTALL_DIR%\\configure_autostart.ps1" -Mode both
if errorlevel 1 (
    echo ⚠️  Error configurando inicio automático
    echo El agente funcionará, pero no se iniciará automáticamente
) else (
    echo ✅ Inicio automático configurado
)

REM Crear acceso directo en escritorio
echo.
echo 🖥️ Creando acceso directo en escritorio...
set DESKTOP=%USERPROFILE%\\Desktop
echo [InternetShortcut] > "%DESKTOP%\\Agente Forense.url"
echo URL=http://localhost:5001 >> "%DESKTOP%\\Agente Forense.url"
echo IconFile=%INSTALL_DIR%\\agent.py >> "%DESKTOP%\\Agente Forense.url"
echo IconIndex=0 >> "%DESKTOP%\\Agente Forense.url"
echo ✅ Acceso directo creado

REM Registrar agente en el servidor
echo.
echo 🌐 Registrando agente en el servidor...
python -c "
import requests
import json
import platform
import socket

try:
    # Obtener información del sistema
    system_info = {
        'os': 'windows',
        'arch': platform.machine(),
        'hostname': socket.gethostname(),
        'user_id': '{{USER_ID}}',
        'capabilities': {
            'dd': True,
            'e01': False,  # Se detectará después
            'aff4': False,  # Se detectará después
            'img': True
        }
    }
    
    # Registrar en el servidor
    response = requests.post('{{SERVER_URL}}/api/agents/register', 
                           json=system_info,
                           headers={'Authorization': 'Bearer {{API_KEY}}'})
    
    if response.status_code == 200:
        print('✅ Agente registrado en el servidor')
    else:
        print('⚠️  Error registrando agente:', response.text)
        
except Exception as e:
    print('⚠️  Error registrando agente:', str(e))
"

echo.
echo ========================================
echo   Instalación Completada
echo ========================================
echo.
echo ✅ AGENTE FORENSE INSTALADO CORRECTAMENTE
echo.
echo 📋 INFORMACIÓN:
echo • Directorio: %INSTALL_DIR%
echo • Evidencias: %EVIDENCE_DIR%
echo • Puerto: 5001
echo • API Key: forensic_agent_2024
echo.
echo 🚀 INICIO AUTOMÁTICO:
echo • El agente se iniciará automáticamente al arrancar el sistema
echo • Para desinstalar: Ejecutar uninstall_autostart.bat
echo.
echo 🌐 ACCESO:
echo • Local: http://localhost:5001
echo • Servidor: {{SERVER_URL}}
echo.
echo ¿Desea iniciar el agente ahora? (S/N)
set /p iniciar=
if /i "%iniciar%"=="S" (
    echo.
    echo Iniciando agente...
    cd /d "%INSTALL_DIR%"
    python agent.py
) else (
    echo.
    echo Para iniciar más tarde: python "%INSTALL_DIR%\\agent.py"
)
echo.
pause
'''

LINUX_INSTALLER_TEMPLATE = '''#!/bin/bash
# Instalador Agente Forense Linux

echo "========================================"
echo "  Instalador Agente Forense Linux"
echo "========================================"
echo

# Verificar si se ejecuta como root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Este instalador requiere permisos de root."
    echo
    echo "Para ejecutar como root:"
    echo "1. sudo ./forensic_agent_linux.sh"
    echo "2. O ejecutar: chmod +x forensic_agent_linux.sh && sudo ./forensic_agent_linux.sh"
    echo
    exit 1
fi

echo "✅ Ejecutándose como root"
echo

# Crear directorio de instalación
INSTALL_DIR="/opt/forensic-agent"
EVIDENCE_DIR="/var/evidencias_forenses"

if [ ! -d "$INSTALL_DIR" ]; then
    mkdir -p "$INSTALL_DIR"
    echo "✅ Directorio de instalación creado: $INSTALL_DIR"
else
    echo "✅ Directorio de instalación ya existe: $INSTALL_DIR"
fi

if [ ! -d "$EVIDENCE_DIR" ]; then
    mkdir -p "$EVIDENCE_DIR"
    chmod 755 "$EVIDENCE_DIR"
    echo "✅ Directorio de evidencias creado: $EVIDENCE_DIR"
else
    echo "✅ Directorio de evidencias ya existe: $EVIDENCE_DIR"
fi

# Copiar archivos del agente
echo
echo "📁 Copiando archivos del agente..."
cp agent.py "$INSTALL_DIR/agent.py"
cp requirements.txt "$INSTALL_DIR/requirements.txt"
cp start_agent.sh "$INSTALL_DIR/start_agent.sh"
cp configure_autostart.sh "$INSTALL_DIR/configure_autostart.sh"
cp uninstall_autostart.sh "$INSTALL_DIR/uninstall_autostart.sh"
cp test_autostart.sh "$INSTALL_DIR/test_autostart.sh"
chmod +x "$INSTALL_DIR"/*.sh
echo "✅ Archivos copiados correctamente"

# Instalar dependencias del sistema
echo
echo "📦 Instalando dependencias del sistema..."
if command -v apt-get &> /dev/null; then
    # Ubuntu/Debian
    apt-get update
    apt-get install -y python3 python3-pip python3-venv smartmontools libewf-tools
elif command -v yum &> /dev/null; then
    # CentOS/RHEL
    yum install -y python3 python3-pip smartmontools libewf-tools
elif command -v dnf &> /dev/null; then
    # Fedora
    dnf install -y python3 python3-pip smartmontools libewf-tools
elif command -v pacman &> /dev/null; then
    # Arch Linux
    pacman -S --noconfirm python python-pip smartmontools libewf
else
    echo "⚠️  No se pudo detectar el gestor de paquetes"
    echo "Instale manualmente: python3, python3-pip, smartmontools, libewf-tools"
fi

# Instalar dependencias Python
echo
echo "📦 Instalando dependencias Python..."
cd "$INSTALL_DIR"
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Error instalando dependencias Python"
    echo
    echo "Soluciones posibles:"
    echo "1. Ejecutar como root"
    echo "2. Usar: python3 -m pip install --user -r requirements.txt"
    echo "3. Crear entorno virtual: python3 -m venv venv"
    exit 1
fi
echo "✅ Dependencias Python instaladas"

# Configurar inicio automático
echo
echo "🚀 Configurando inicio automático..."
"$INSTALL_DIR/configure_autostart.sh"
if [ $? -ne 0 ]; then
    echo "⚠️  Error configurando inicio automático"
    echo "El agente funcionará, pero no se iniciará automáticamente"
else
    echo "✅ Inicio automático configurado"
fi

# Crear usuario del sistema
echo
echo "👤 Creando usuario del sistema..."
if ! id "forensic-agent" &>/dev/null; then
    useradd -r -s /bin/false -d "$INSTALL_DIR" forensic-agent
    chown -R forensic-agent:forensic-agent "$INSTALL_DIR"
    chown -R forensic-agent:forensic-agent "$EVIDENCE_DIR"
    echo "✅ Usuario forensic-agent creado"
else
    echo "✅ Usuario forensic-agent ya existe"
fi

# Registrar agente en el servidor
echo
echo "🌐 Registrando agente en el servidor..."
python3 -c "
import requests
import json
import platform
import socket

try:
    # Obtener información del sistema
    system_info = {
        'os': 'linux',
        'arch': platform.machine(),
        'hostname': socket.gethostname(),
        'user_id': '{{USER_ID}}',
        'capabilities': {
            'dd': True,
            'e01': True,  # libewf-tools instalado
            'aff4': False,  # Se detectará después
            'img': True
        }
    }
    
    # Registrar en el servidor
    response = requests.post('{{SERVER_URL}}/api/agents/register', 
                           json=system_info,
                           headers={'Authorization': 'Bearer {{API_KEY}}'})
    
    if response.status_code == 200:
        print('✅ Agente registrado en el servidor')
    else:
        print('⚠️  Error registrando agente:', response.text)
        
except Exception as e:
    print('⚠️  Error registrando agente:', str(e))
"

echo
echo "========================================"
echo "  Instalación Completada"
echo "========================================"
echo
echo "✅ AGENTE FORENSE INSTALADO CORRECTAMENTE"
echo
echo "📋 INFORMACIÓN:"
echo "• Directorio: $INSTALL_DIR"
echo "• Evidencias: $EVIDENCE_DIR"
echo "• Puerto: 5001"
echo "• API Key: forensic_agent_2024"
echo
echo "🚀 INICIO AUTOMÁTICO:"
echo "• El agente se iniciará automáticamente al arrancar el sistema"
echo "• Para desinstalar: $INSTALL_DIR/uninstall_autostart.sh"
echo
echo "🌐 ACCESO:"
echo "• Local: http://localhost:5001"
echo "• Servidor: {{SERVER_URL}}"
echo
echo "¿Desea iniciar el agente ahora? (s/n)"
read -r iniciar
if [ "$iniciar" = "s" ] || [ "$iniciar" = "S" ]; then
    echo
    echo "Iniciando agente..."
    cd "$INSTALL_DIR"
    python3 agent.py
else
    echo
    echo "Para iniciar más tarde: python3 $INSTALL_DIR/agent.py"
fi
echo
'''

MACOS_INSTALLER_TEMPLATE = '''#!/bin/bash
# Instalador Agente Forense macOS

echo "========================================"
echo "  Instalador Agente Forense macOS"
echo "========================================"
echo

# Verificar si se ejecuta como root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Este instalador requiere permisos de administrador."
    echo
    echo "Para ejecutar como administrador:"
    echo "1. sudo ./forensic_agent_macos.sh"
    echo "2. O ejecutar: chmod +x forensic_agent_macos.sh && sudo ./forensic_agent_macos.sh"
    echo
    exit 1
fi

echo "✅ Ejecutándose como administrador"
echo

# Crear directorio de instalación
INSTALL_DIR="/Applications/ForensicAgent"
EVIDENCE_DIR="/Users/Shared/evidencias_forenses"

if [ ! -d "$INSTALL_DIR" ]; then
    mkdir -p "$INSTALL_DIR"
    echo "✅ Directorio de instalación creado: $INSTALL_DIR"
else
    echo "✅ Directorio de instalación ya existe: $INSTALL_DIR"
fi

if [ ! -d "$EVIDENCE_DIR" ]; then
    mkdir -p "$EVIDENCE_DIR"
    chmod 755 "$EVIDENCE_DIR"
    echo "✅ Directorio de evidencias creado: $EVIDENCE_DIR"
else
    echo "✅ Directorio de evidencias ya existe: $EVIDENCE_DIR"
fi

# Copiar archivos del agente
echo
echo "📁 Copiando archivos del agente..."
cp agent.py "$INSTALL_DIR/agent.py"
cp requirements.txt "$INSTALL_DIR/requirements.txt"
cp start_agent.sh "$INSTALL_DIR/start_agent.sh"
cp configure_autostart.sh "$INSTALL_DIR/configure_autostart.sh"
cp uninstall_autostart.sh "$INSTALL_DIR/uninstall_autostart.sh"
cp test_autostart.sh "$INSTALL_DIR/test_autostart.sh"
chmod +x "$INSTALL_DIR"/*.sh
echo "✅ Archivos copiados correctamente"

# Instalar dependencias del sistema
echo
echo "📦 Instalando dependencias del sistema..."
if command -v brew &> /dev/null; then
    # Homebrew
    brew install python3 smartmontools libewf
else
    echo "⚠️  Homebrew no encontrado"
    echo "Instale Homebrew desde https://brew.sh/"
    echo "Luego ejecute: brew install python3 smartmontools libewf"
fi

# Instalar dependencias Python
echo
echo "📦 Instalando dependencias Python..."
cd "$INSTALL_DIR"
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Error instalando dependencias Python"
    echo
    echo "Soluciones posibles:"
    echo "1. Ejecutar como administrador"
    echo "2. Usar: python3 -m pip install --user -r requirements.txt"
    echo "3. Crear entorno virtual: python3 -m venv venv"
    exit 1
fi
echo "✅ Dependencias Python instaladas"

# Configurar inicio automático
echo
echo "🚀 Configurando inicio automático..."
"$INSTALL_DIR/configure_autostart.sh"
if [ $? -ne 0 ]; then
    echo "⚠️  Error configurando inicio automático"
    echo "El agente funcionará, pero no se iniciará automáticamente"
else
    echo "✅ Inicio automático configurado"
fi

# Crear usuario del sistema
echo
echo "👤 Creando usuario del sistema..."
if ! id "forensic-agent" &>/dev/null; then
    dscl . -create /Users/forensic-agent
    dscl . -create /Users/forensic-agent UserShell /bin/false
    dscl . -create /Users/forensic-agent RealName "Forensic Agent"
    dscl . -create /Users/forensic-agent UniqueID 502
    dscl . -create /Users/forensic-agent PrimaryGroupID 20
    dscl . -create /Users/forensic-agent NFSHomeDirectory "$INSTALL_DIR"
    chown -R forensic-agent:staff "$INSTALL_DIR"
    chown -R forensic-agent:staff "$EVIDENCE_DIR"
    echo "✅ Usuario forensic-agent creado"
else
    echo "✅ Usuario forensic-agent ya existe"
fi

# Registrar agente en el servidor
echo
echo "🌐 Registrando agente en el servidor..."
python3 -c "
import requests
import json
import platform
import socket

try:
    # Obtener información del sistema
    system_info = {
        'os': 'macos',
        'arch': platform.machine(),
        'hostname': socket.gethostname(),
        'user_id': '{{USER_ID}}',
        'capabilities': {
            'dd': True,
            'e01': True,  # libewf instalado
            'aff4': False,  # Se detectará después
            'img': True
        }
    }
    
    # Registrar en el servidor
    response = requests.post('{{SERVER_URL}}/api/agents/register', 
                           json=system_info,
                           headers={'Authorization': 'Bearer {{API_KEY}}'})
    
    if response.status_code == 200:
        print('✅ Agente registrado en el servidor')
    else:
        print('⚠️  Error registrando agente:', response.text)
        
except Exception as e:
    print('⚠️  Error registrando agente:', str(e))
"

echo
echo "========================================"
echo "  Instalación Completada"
echo "========================================"
echo
echo "✅ AGENTE FORENSE INSTALADO CORRECTAMENTE"
echo
echo "📋 INFORMACIÓN:"
echo "• Directorio: $INSTALL_DIR"
echo "• Evidencias: $EVIDENCE_DIR"
echo "• Puerto: 5001"
echo "• API Key: forensic_agent_2024"
echo
echo "🚀 INICIO AUTOMÁTICO:"
echo "• El agente se iniciará automáticamente al arrancar el sistema"
echo "• Para desinstalar: $INSTALL_DIR/uninstall_autostart.sh"
echo
echo "🌐 ACCESO:"
echo "• Local: http://localhost:5001"
echo "• Servidor: {{SERVER_URL}}"
echo
echo "¿Desea iniciar el agente ahora? (s/n)"
read -r iniciar
if [ "$iniciar" = "s" ] || [ "$iniciar" = "S" ]; then
    echo
    echo "Iniciando agente..."
    cd "$INSTALL_DIR"
    python3 agent.py
else
    echo
    echo "Para iniciar más tarde: python3 $INSTALL_DIR/agent.py"
fi
echo
'''

# ==================== RUTAS API ====================

@installer_bp.route('/generate', methods=['POST'])
def generate_installer():
    """Genera un instalador personalizado para el sistema del usuario"""
    try:
        data = request.get_json()
        system_info = data.get('system', {})
        user_id = data.get('user_id', 'anonymous')
        
        # Validar datos
        if not system_info.get('os'):
            return jsonify({'error': 'Información del sistema requerida'}), 400
        
        os_type = system_info['os']
        arch = system_info.get('arch', 'x64')
        
        # Generar instalador
        installer_path = create_installer(os_type, arch, user_id, system_info)
        
        if installer_path:
            return send_file(installer_path, as_attachment=True)
        else:
            return jsonify({'error': 'Error generando instalador'}), 500
            
    except Exception as e:
        logger.error(f"Error generando instalador: {e}")
        return jsonify({'error': str(e)}), 500

@installer_bp.route('/templates', methods=['GET'])
def list_templates():
    """Lista las plantillas de instaladores disponibles"""
    try:
        templates = []
        
        # Plantillas disponibles
        available_templates = [
            {'os': 'windows', 'arch': 'x64', 'name': 'Windows 64-bit'},
            {'os': 'windows', 'arch': 'x86', 'name': 'Windows 32-bit'},
            {'os': 'linux', 'arch': 'x64', 'name': 'Linux 64-bit'},
            {'os': 'linux', 'arch': 'arm64', 'name': 'Linux ARM64'},
            {'os': 'macos', 'arch': 'x64', 'name': 'macOS Intel'},
            {'os': 'macos', 'arch': 'arm64', 'name': 'macOS Apple Silicon'}
        ]
        
        return jsonify({
            'status': 'success',
            'templates': available_templates
        })
        
    except Exception as e:
        logger.error(f"Error listando plantillas: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== FUNCIONES AUXILIARES ====================

def create_installer(os_type, arch, user_id, system_info):
    """Crea un instalador personalizado"""
    try:
        # Crear directorio temporal
        with tempfile.TemporaryDirectory() as temp_dir:
            installer_dir = os.path.join(temp_dir, 'installer')
            os.makedirs(installer_dir, exist_ok=True)
            
            # Seleccionar plantilla
            if os_type == 'windows':
                template = WINDOWS_INSTALLER_TEMPLATE
                installer_name = f'forensic_agent_windows_{arch}_{user_id}.exe'
            elif os_type == 'linux':
                template = LINUX_INSTALLER_TEMPLATE
                installer_name = f'forensic_agent_linux_{arch}_{user_id}.sh'
            elif os_type == 'macos':
                template = MACOS_INSTALLER_TEMPLATE
                installer_name = f'forensic_agent_macos_{arch}_{user_id}.sh'
            else:
                raise ValueError(f"Sistema operativo no soportado: {os_type}")
            
            # Personalizar plantilla
            personalized_template = personalize_template(template, user_id, system_info)
            
            # Crear archivo de instalador
            installer_path = os.path.join(installer_dir, installer_name)
            with open(installer_path, 'w', encoding='utf-8') as f:
                f.write(personalized_template)
            
            # Hacer ejecutable en Unix
            if os_type in ['linux', 'macos']:
                os.chmod(installer_path, 0o755)
            
            # Copiar archivos del agente
            copy_agent_files(installer_dir, os_type)
            
            # Reemplazar configure_autostart.ps1 con la versión corregida
            if os_type == 'windows':
                fixed_ps1_path = 'agente_windows/configure_autostart_fixed.ps1'
                if os.path.exists(fixed_ps1_path):
                    shutil.copy2(fixed_ps1_path, os.path.join(installer_dir, 'configure_autostart.ps1'))
            
            # Crear archivo ZIP
            zip_path = os.path.join(GENERATED_INSTALLERS_DIR, f'{installer_name}.zip')
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(installer_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, installer_dir)
                        zipf.write(file_path, arcname)
            
            return zip_path
            
    except Exception as e:
        logger.error(f"Error creando instalador: {e}")
        return None

def personalize_template(template, user_id, system_info):
    """Personaliza la plantilla con información del usuario"""
    # Obtener configuración del servidor
    server_url = request.host_url.rstrip('/')
    api_key = 'forensic_agent_2024'  # En producción, usar variable de entorno
    
    # Reemplazar placeholders
    personalized = template.replace('{{USER_ID}}', user_id)
    personalized = personalized.replace('{{SERVER_URL}}', server_url)
    personalized = personalized.replace('{{API_KEY}}', api_key)
    
    return personalized

def copy_agent_files(installer_dir, os_type):
    """Copia los archivos del agente al directorio del instalador"""
    try:
        # Archivos base del agente
        agent_files = [
            'agent.py',
            'requirements.txt',
            'README.md'
        ]
        
        # Archivos específicos del SO (versión simplificada)
        if os_type == 'windows':
            agent_files.extend([
                'install.ps1',      # Instalador PowerShell completo
                'install.bat',      # Instalador CMD básico
                'test.bat'          # Probador del agente
            ])
        else:  # Linux/macOS
            agent_files.extend([
                'install.sh',       # Instalador shell completo
                'test.sh'           # Probador del agente
            ])
        
        # Copiar archivos desde el directorio del agente
        agent_source_dir = 'agente_windows'
        for file_name in agent_files:
            source_path = os.path.join(agent_source_dir, file_name)
            if os.path.exists(source_path):
                dest_path = os.path.join(installer_dir, file_name)
                shutil.copy2(source_path, dest_path)
            else:
                logger.warning(f"Archivo no encontrado: {source_path}")
                
    except Exception as e:
        logger.error(f"Error copiando archivos del agente: {e}")

# ==================== REGISTRO DE AGENTES ====================

@installer_bp.route('/agents/register', methods=['POST'])
def register_agent():
    """Registra un nuevo agente en el sistema"""
    try:
        data = request.get_json()
        
        # Validar datos
        required_fields = ['os', 'arch', 'hostname', 'user_id', 'capabilities']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo requerido: {field}'}), 400
        
        # Crear registro del agente
        agent_info = {
            'id': f"agent_{data['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'user_id': data['user_id'],
            'os': data['os'],
            'arch': data['arch'],
            'hostname': data['hostname'],
            'capabilities': data['capabilities'],
            'status': 'active',
            'registered_at': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'endpoint': f"http://{data.get('hostname', 'localhost')}:5001"
        }
        
        # Guardar en base de datos (implementar según tu modelo)
        # db.agents.insert(agent_info)
        
        logger.info(f"Agente registrado: {agent_info['id']}")
        
        return jsonify({
            'status': 'success',
            'agent_id': agent_info['id'],
            'message': 'Agente registrado correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error registrando agente: {e}")
        return jsonify({'error': str(e)}), 500

@installer_bp.route('/agents', methods=['GET'])
def list_agents():
    """Lista todos los agentes registrados"""
    try:
        # Obtener agentes de la base de datos
        # agents = db.agents.find_all()
        
        # Simular datos para demo
        agents = [
            {
                'id': 'agent_demo_001',
                'user_id': 'demo_user',
                'os': 'windows',
                'arch': 'x64',
                'hostname': 'DESKTOP-ABC123',
                'status': 'active',
                'last_seen': datetime.now().isoformat()
            }
        ]
        
        return jsonify({
            'status': 'success',
            'agents': agents,
            'count': len(agents)
        })
        
    except Exception as e:
        logger.error(f"Error listando agentes: {e}")
        return jsonify({'error': str(e)}), 500
