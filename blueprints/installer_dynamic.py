#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blueprint para generación dinámica de instaladores
Usa Inno Setup con Wine para compilar instaladores personalizados
"""

import os
import json
import uuid
import tempfile
import subprocess
import shutil
from datetime import datetime
from flask import Blueprint, request, send_from_directory, current_app, jsonify
from flask_login import login_required, current_user

# Crear blueprint
installer_dynamic_bp = Blueprint('installer_dynamic', __name__, url_prefix='/api/installer-dynamic')

# Configuración
PREBUILT_AGENTS_DIR = "/prebuilt_agents"
TEMPLATES_DIR = "installer_templates"
BUILD_DIR = "/tmp/installer_builds"

def ensure_directories():
    """Asegura que los directorios necesarios existan"""
    os.makedirs(BUILD_DIR, exist_ok=True)

def render_innosetup_template(template_path, **kwargs):
    """Renderiza la plantilla de Inno Setup con los parámetros dados"""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Reemplazar variables en la plantilla
        for key, value in kwargs.items():
            template_content = template_content.replace(f"{{{{ {key} }}}}", str(value))
        
        return template_content
    except Exception as e:
        current_app.logger.error(f"Error renderizando plantilla: {e}")
        return None

def compile_installer_with_wine(script_path, build_dir):
    """Compila el instalador usando Wine e Inno Setup"""
    try:
        # Comando para compilar con Wine
        cmd = [
            'wine', 'ISCC.exe', 
            script_path.replace('/', '\\'),  # Convertir a ruta Windows
            f'/O"{build_dir}"'  # Directorio de salida
        ]
        
        current_app.logger.info(f"Ejecutando comando Wine: {' '.join(cmd)}")
        
        # Ejecutar compilación
        result = subprocess.run(
            cmd, 
            cwd=build_dir,
            capture_output=True, 
            text=True, 
            timeout=120
        )
        
        if result.returncode == 0:
            current_app.logger.info("Compilación exitosa")
            current_app.logger.info(f"Stdout: {result.stdout}")
            return True
        else:
            current_app.logger.error(f"Error en compilación: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        current_app.logger.error("Timeout en compilación")
        return False
    except Exception as e:
        current_app.logger.error(f"Error ejecutando Wine: {e}")
        return False

@installer_dynamic_bp.route('/generate/windows', methods=['POST'])
@login_required
def generate_windows_installer():
    """Genera un instalador Windows personalizado"""
    try:
        # Obtener datos de la request
        data = request.json or {}
        user_id = current_user.id
        server_url = request.host_url.strip('/')
        
        # Generar token único para registro
        registration_token = str(uuid.uuid4())
        
        # Crear directorio temporal para la compilación
        with tempfile.TemporaryDirectory() as temp_dir:
            build_dir = os.path.join(temp_dir, "build")
            os.makedirs(build_dir, exist_ok=True)
            
            # Ruta al agente pre-compilado
            agent_exe_path = os.path.join(PREBUILT_AGENTS_DIR, "AgenteForense.exe")
            
            # Verificar que el agente existe
            if not os.path.exists(agent_exe_path):
                return jsonify({
                    'error': 'Agente pre-compilado no encontrado'
                }), 404
            
            # Copiar agente al directorio de compilación
            agent_target = os.path.join(build_dir, "AgenteForense.exe")
            shutil.copy2(agent_exe_path, agent_target)
            
            # Ruta a la plantilla
            template_path = os.path.join(current_app.root_path, TEMPLATES_DIR, "agente_template.iss")
            if not os.path.exists(template_path):
                # Usar plantilla del directorio raíz si no existe en templates
                template_path = os.path.join(current_app.root_path, "agente_template.iss")
            
            if not os.path.exists(template_path):
                return jsonify({
                    'error': 'Plantilla de Inno Setup no encontrada'
                }), 404
            
            # Renderizar plantilla
            script_content = render_innosetup_template(
                template_path,
                user_id=user_id,
                build_dir=build_dir.replace('/', '\\'),  # Ruta Windows
                agent_exe_path=agent_target.replace('/', '\\'),  # Ruta Windows
                server_url=server_url,
                registration_token=registration_token
            )
            
            if not script_content:
                return jsonify({
                    'error': 'Error renderizando plantilla'
                }), 500
            
            # Guardar script renderizado
            script_path = os.path.join(build_dir, "installer.iss")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Compilar instalador
            if not compile_installer_with_wine(script_path, build_dir):
                return jsonify({
                    'error': 'Error compilando instalador con Wine'
                }), 500
            
            # Buscar el instalador generado
            installer_name = f"Instalador-Agente-{user_id}.exe"
            installer_path = os.path.join(build_dir, installer_name)
            
            if not os.path.exists(installer_path):
                # Buscar cualquier archivo .exe en el directorio
                exe_files = [f for f in os.listdir(build_dir) if f.endswith('.exe')]
                if exe_files:
                    installer_name = exe_files[0]
                    installer_path = os.path.join(build_dir, installer_name)
                else:
                    return jsonify({
                        'error': 'Instalador no generado correctamente'
                    }), 500
            
            # TODO: Guardar token en BD para validación posterior
            # save_registration_token(user_id, registration_token)
            
            # Enviar archivo
            return send_from_directory(
                build_dir,
                installer_name,
                as_attachment=True,
                download_name=f"InstaladorAgenteForense_{user_id}.exe"
            )
            
    except Exception as e:
        current_app.logger.error(f"Error generando instalador: {e}")
        return jsonify({
            'error': f'Error interno: {str(e)}'
        }), 500

@installer_dynamic_bp.route('/status', methods=['GET'])
def get_compilation_status():
    """Obtiene el estado del sistema de compilación"""
    try:
        # Verificar Wine
        wine_available = False
        try:
            result = subprocess.run(['wine', '--version'], capture_output=True, text=True, timeout=5)
            wine_available = result.returncode == 0
        except:
            pass
        
        # Verificar Inno Setup
        innosetup_available = False
        try:
            result = subprocess.run(['wine', 'ISCC.exe', '/?'], capture_output=True, text=True, timeout=5)
            innosetup_available = result.returncode == 0
        except:
            pass
        
        # Verificar agente pre-compilado
        agent_available = os.path.exists(os.path.join(PREBUILT_AGENTS_DIR, "AgenteForense.exe"))
        
        # Verificar plantilla
        template_path = os.path.join(current_app.root_path, TEMPLATES_DIR, "agente_template.iss")
        if not os.path.exists(template_path):
            template_path = os.path.join(current_app.root_path, "agente_template.iss")
        template_available = os.path.exists(template_path)
        
        return jsonify({
            'status': 'success',
            'compilation_system': {
                'wine_available': wine_available,
                'innosetup_available': innosetup_available,
                'agent_available': agent_available,
                'template_available': template_available,
                'ready': wine_available and innosetup_available and agent_available and template_available
            },
            'paths': {
                'prebuilt_agents_dir': PREBUILT_AGENTS_DIR,
                'templates_dir': TEMPLATES_DIR,
                'build_dir': BUILD_DIR
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo estado: {e}")
        return jsonify({
            'error': f'Error interno: {str(e)}'
        }), 500

@installer_dynamic_bp.route('/test', methods=['POST'])
@login_required
def test_compilation():
    """Prueba el sistema de compilación sin generar archivo final"""
    try:
        # Crear un script de prueba simple
        test_script = """
[Setup]
AppName=Test Installer
AppVersion=1.0.0
DefaultDirName={autopf}\\TestApp
OutputBaseFilename=test_installer
PrivilegesRequired=admin

[Files]
Source: "test.txt"; DestDir: "{app}"; Flags: ignoreversion

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crear archivo de prueba
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("Test file content")
            
            # Guardar script de prueba
            script_path = os.path.join(temp_dir, "test.iss")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(test_script)
            
            # Intentar compilar
            success = compile_installer_with_wine(script_path, temp_dir)
            
            return jsonify({
                'status': 'success' if success else 'error',
                'message': 'Compilación de prueba exitosa' if success else 'Error en compilación de prueba'
            })
            
    except Exception as e:
        current_app.logger.error(f"Error en prueba de compilación: {e}")
        return jsonify({
            'error': f'Error interno: {str(e)}'
        }), 500

