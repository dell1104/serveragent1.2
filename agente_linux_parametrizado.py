#!/usr/bin/env python3
"""
Agente Forense para Linux
Versión parametrizada que acepta servidor y token como parámetros
"""

import os
import sys
import json
import time
import psutil
import requests
import argparse
import subprocess
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

# Configuración por defecto
DEFAULT_CONFIG = {
    'server_url': 'http://localhost:8080',
    'token': '',
    'user_id': '',
    'agente_id': '',
    'api_key': '',
    'puerto_local': 5001,
    'intervalo_heartbeat': 30
}

# Configuración global
AGENT_CONFIG = DEFAULT_CONFIG.copy()

def parse_arguments():
    """Parsea los argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(description='Agente Forense Linux')
    parser.add_argument('--server_url', required=True, help='URL del servidor principal')
    parser.add_argument('--token', required=True, help='Token de registro')
    parser.add_argument('--user_id', help='ID del usuario')
    parser.add_argument('--puerto', type=int, default=5001, help='Puerto local del agente')
    return parser.parse_args()

def cargar_configuracion():
    """Carga la configuración desde archivo o argumentos"""
    args = parse_arguments()
    
    # Configuración desde argumentos
    AGENT_CONFIG['server_url'] = args.server_url
    AGENT_CONFIG['token'] = args.token
    AGENT_CONFIG['user_id'] = args.user_id or 'unknown'
    AGENT_CONFIG['puerto_local'] = args.puerto
    
    # Cargar configuración guardada si existe
    config_path = os.path.expanduser('~/.config/sistema-forense-agente/config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                saved_config = json.load(f)
                AGENT_CONFIG.update(saved_config)
        except Exception as e:
            print(f"Error cargando configuración: {e}")
    
    return AGENT_CONFIG

def guardar_configuracion(config):
    """Guarda la configuración en archivo"""
    config_dir = os.path.expanduser('~/.config/sistema-forense-agente')
    os.makedirs(config_dir, exist_ok=True)
    
    config_path = os.path.join(config_dir, 'config.json')
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Configuración guardada en: {config_path}")
    except Exception as e:
        print(f"Error guardando configuración: {e}")

def registrar_con_token(server_url, token, user_id):
    """Registra el agente con el servidor usando token"""
    try:
        # Asegurar que use el puerto correcto
        if not ':8080' in server_url and not ':5000' in server_url:
            server_url = f"{server_url}:8080"
        
        url = f"{server_url}/api/agentes/registrar"
        
        datos = {
            'token': token,
            'user_id': user_id,
            'sistema_operativo': 'Linux',
            'version': '1.0',
            'capacidades': ['dd', 'aff4', 'e01']
        }
        
        print(f"Intentando conectar a: {url}")
        print(f"Datos: {datos}")
        
        response = requests.post(url, json=datos, timeout=30)
        
        print(f"Respuesta del servidor: {response.status_code}")
        print(f"Contenido: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                AGENT_CONFIG['agente_id'] = data.get('agente_id', '')
                AGENT_CONFIG['api_key'] = data.get('api_key', '')
                guardar_configuracion(AGENT_CONFIG)
                print("✓ Registro exitoso")
                return True
            else:
                print(f"✗ Error en registro: {data.get('error', 'Error desconocido')}")
                return False
        else:
            print(f"✗ Error HTTP: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Error de conexión: {e}")
        return False
    except Exception as e:
        print(f"✗ Error inesperado: {e}")
        return False

def obtener_info_sistema():
    """Obtiene información del sistema Linux"""
    try:
        # Información básica del sistema
        info = {
            'hostname': os.uname().nodename,
            'sistema': os.uname().sysname,
            'version': os.uname().release,
            'arquitectura': os.uname().machine,
            'cpu_count': psutil.cpu_count(),
            'memoria_total': psutil.virtual_memory().total,
            'memoria_disponible': psutil.virtual_memory().available,
            'disco_total': sum(psutil.disk_usage(part.mountpoint).total for part in psutil.disk_partitions()),
            'disco_disponible': sum(psutil.disk_usage(part.mountpoint).free for part in psutil.disk_partitions()),
            'uptime': time.time() - psutil.boot_time(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Información de discos
        discos = []
        for part in psutil.disk_partitions():
            try:
                uso = psutil.disk_usage(part.mountpoint)
                disco = {
                    'dispositivo': part.device,
                    'punto_montaje': part.mountpoint,
                    'tipo_sistema': part.fstype,
                    'tamaño_total': uso.total,
                    'tamaño_usado': uso.used,
                    'tamaño_libre': uso.free,
                    'porcentaje_usado': (uso.used / uso.total) * 100
                }
                discos.append(disco)
            except PermissionError:
                continue
        
        info['discos'] = discos
        
        return info
        
    except Exception as e:
        print(f"Error obteniendo información del sistema: {e}")
        return {}

def enviar_heartbeat(server_url, agente_id, api_key):
    """Envía heartbeat al servidor"""
    try:
        url = f"{server_url}/api/agentes/heartbeat"
        headers = {'Authorization': f'Bearer {api_key}'}
        data = {
            'agente_id': agente_id,
            'timestamp': datetime.now().isoformat(),
            'estado': 'activo'
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error enviando heartbeat: {e}")
        return False

# Crear aplicación Flask
app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    """Página principal del agente"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agente Forense Linux</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
            h1 { color: #333; }
            .info-item { margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🖥️ Agente Forense Linux</h1>
            <div class="status success">
                <strong>Estado:</strong> Activo y conectado
            </div>
            <div class="status info">
                <strong>Servidor:</strong> ''' + AGENT_CONFIG.get('server_url', 'No configurado') + '''<br>
                <strong>ID del Agente:</strong> ''' + AGENT_CONFIG.get('agente_id', 'No registrado') + '''<br>
                <strong>Puerto Local:</strong> ''' + str(AGENT_CONFIG.get('puerto_local', 5001)) + '''
            </div>
            <p>Este agente está ejecutándose y monitoreando el sistema.</p>
            <p>Para gestionar el agente, usa el servidor principal.</p>
        </div>
    </body>
    </html>
    '''

@app.route('/api/status')
def status():
    """Endpoint de estado del agente"""
    return jsonify({
        'estado': 'activo',
        'agente_id': AGENT_CONFIG.get('agente_id', ''),
        'sistema': 'Linux',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/sistema')
def sistema():
    """Endpoint de información del sistema"""
    return jsonify(obtener_info_sistema())

@app.route('/api/discos')
def discos():
    """Endpoint de información de discos"""
    info = obtener_info_sistema()
    return jsonify(info.get('discos', []))

def bucle_principal(config):
    """Bucle principal del agente"""
    agente_id = config.get('agente_id', config.get('id', 'Unknown'))
    print(f"Agente iniciado con configuración: {agente_id}")
    
    # Registrar con el servidor
    if not registrar_con_token(config['server_url'], config['token'], config['user_id']):
        print("No se pudo registrar con el servidor. Continuando en modo local...")
    
    # Iniciar servidor web local
    print(f"Iniciando servidor local en puerto {config['puerto_local']}...")
    
    # Ejecutar en hilo separado para no bloquear
    import threading
    
    def run_server():
        app.run(host='0.0.0.0', port=config['puerto_local'], debug=False)
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Bucle de heartbeat
    while True:
        try:
            if config.get('agente_id') and config.get('api_key'):
                enviar_heartbeat(config['server_url'], config['agente_id'], config['api_key'])
            time.sleep(config.get('intervalo_heartbeat', 30))
        except KeyboardInterrupt:
            print("\nDeteniendo agente...")
            break
        except Exception as e:
            print(f"Error en bucle principal: {e}")
            time.sleep(10)

if __name__ == '__main__':
    print("=== AGENTE FORENSE LINUX ===")
    
    # Cargar configuración
    config = cargar_configuracion()
    
    # Mostrar configuración
    print(f"Servidor: {config['server_url']}")
    print(f"Usuario: {config['user_id']}")
    print(f"Token: {config['token'][:8]}...")
    print()
    
    # Ejecutar bucle principal
    bucle_principal(config)
