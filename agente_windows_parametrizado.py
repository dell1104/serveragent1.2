#!/usr/bin/env python3
"""
Agente Forense Windows - Con Parámetros
Se ejecuta localmente en Windows del usuario
"""

import argparse
import ctypes
import json
import os
import sys
import threading
import time
import requests
import psutil
import webbrowser
from flask import Flask, Response, jsonify
from flask_cors import CORS
import wmi

app = Flask(__name__)
CORS(app)

# --- VARIABLES GLOBALES ---
AGENT_CONFIG = {
    'id': None,
    'name': 'Agente Forense Windows',
    'version': '1.0.0',
    'server_url': None,
    'api_key': None,
    'token': None
}

def get_config_path():
    """Obtiene la ruta a la carpeta de configuración en AppData."""
    app_data_path = os.getenv('APPDATA')
    config_dir = os.path.join(app_data_path, 'SistemaForenseAgente')
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'config.json')

def guardar_configuracion(server_url, api_key, agente_id, token):
    """Guarda la configuración en un archivo JSON."""
    config_path = get_config_path()
    config_data = {
        'server_url': server_url,
        'api_key': api_key,
        'agente_id': agente_id,
        'token': token
    }
    with open(config_path, 'w') as f:
        json.dump(config_data, f, indent=4)
    print(f"Configuración guardada en {config_path}")

def mostrar_error(mensaje):
    """Muestra un popup de error al usuario."""
    ctypes.windll.user32.MessageBoxW(0, mensaje, "Error - Agente Forense", 0x10 | 0x0)

def mostrar_info(mensaje):
    """Muestra un popup de información al usuario."""
    ctypes.windll.user32.MessageBoxW(0, mensaje, "Agente Forense", 0x40 | 0x0)

def registrar_con_token(server_url, token):
    """Se registra en el servidor usando un token de un solo uso."""
    try:
        # Generar ID único del agente
        agente_id = f"AGENTE_{psutil.boot_time()}_{os.getpid()}"
        
        payload = {
            'agente_id': agente_id,
            'token': token,
            'platform': 'Windows',
            'python_version': sys.version,
            'capabilities': ['DD', 'E01', 'AFF4']
        }
        
        # Asegurar que la URL termine con puerto correcto
        if not server_url.startswith('http'):
            server_url = f"http://{server_url}"
        
        # Asegurar que use el puerto 8080 (Nginx)
        if not ':8080' in server_url and not ':5000' in server_url:
            server_url = f"{server_url}:8080"
        
        print(f"Intentando conectar a: {server_url}/api/agentes/registrar")
        
        response = requests.post(f"{server_url}/api/agentes/registrar", json=payload, timeout=30)
        
        print(f"Respuesta del servidor: {response.status_code}")
        print(f"Contenido: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            api_key = data.get('api_key')
            print(f"Registro exitoso. API Key recibida: {api_key[:8]}...")
            return api_key, agente_id
        else:
            try:
                error_msg = response.json().get('error', 'Error desconocido')
            except:
                error_msg = f"Error HTTP {response.status_code}: {response.text[:100]}"
            mostrar_error(f"El registro en el servidor falló: {error_msg}")
            return None, None
    except requests.RequestException as e:
        mostrar_error(f"No se pudo conectar al servidor en {server_url}.\nError: {e}")
        return None, None

def configurar_inicio_automatico():
    """Configura el agente para que se inicie con Windows usando Tareas Programadas."""
    executable_path = sys.executable
    command = f'schtasks /Create /TN "AgenteForense" /TR "\'{executable_path}\'" /SC ONLOGON /RL HIGHEST /F'
    try:
        import subprocess
        subprocess.run(command, check=True, shell=True, capture_output=True)
        print("Inicio automático configurado correctamente.")
        return True
    except subprocess.CalledProcessError as e:
        mostrar_error(f"No se pudo configurar el inicio automático. ¿El instalador se ejecutó como Administrador?\nError: {e.stderr.decode()}")
        return False

def get_system_info():
    """Obtener información del sistema Windows"""
    try:
        c = wmi.WMI()
        system = c.Win32_ComputerSystem()[0]
        os_info = c.Win32_OperatingSystem()[0]
        
        return {
            'hostname': system.Name,
            'platform': 'Windows',
            'architecture': os_info.OSArchitecture,
            'python_version': sys.version,
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_usage': psutil.disk_usage('C:\\').percent,
            'cpu_count': psutil.cpu_count(),
            'os_version': os_info.Caption,
            'manufacturer': system.Manufacturer,
            'model': system.Model
        }
    except Exception as e:
        return {
            'hostname': 'Unknown',
            'platform': 'Windows',
            'architecture': 'Unknown',
            'python_version': sys.version,
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_usage': psutil.disk_usage('C:\\').percent,
            'cpu_count': psutil.cpu_count()
        }

def list_available_disks():
    """Listar discos físicos disponibles en Windows"""
    disks = []
    
    try:
        c = wmi.WMI()
        physical_disks = c.Win32_DiskDrive()
        
        for disk in physical_disks:
            try:
                # Obtener información de la partición
                partitions = c.Win32_LogicalDiskToPartition()
                disk_partitions = []
                
                for partition in partitions:
                    if partition.Antecedent.DeviceID == disk.DeviceID:
                        logical_disk = c.Win32_LogicalDisk(DeviceID=partition.Dependent.DeviceID)[0]
                        disk_partitions.append({
                            'drive_letter': logical_disk.DeviceID,
                            'size': logical_disk.Size,
                            'free_space': logical_disk.FreeSpace,
                            'file_system': logical_disk.FileSystem
                        })
                
                # Información del disco físico
                disk_info = {
                    'device_id': disk.DeviceID,
                    'model': disk.Model,
                    'size': disk.Size,
                    'interface_type': disk.InterfaceType,
                    'media_type': disk.MediaType,
                    'partitions': disk_partitions,
                    'is_physical': True,
                    'readable': True,
                    'writable': False
                }
                
                # Agregar información de tamaño legible
                if disk.Size:
                    size_gb = disk.Size / (1024**3)
                    disk_info['size_gb'] = round(size_gb, 2)
                    disk_info['size_human'] = f"{disk_info['size_gb']} GB"
                
                disks.append(disk_info)
                
            except Exception as e:
                print(f"Error procesando disco {disk.DeviceID}: {e}")
                continue
                
    except Exception as e:
        print(f"Error obteniendo discos: {e}")
        # Fallback usando psutil
        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info = {
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total_size': usage.total,
                    'used_size': usage.used,
                    'free_size': usage.free,
                    'readable': os.access(partition.mountpoint, os.R_OK),
                    'writable': os.access(partition.mountpoint, os.W_OK),
                    'is_physical': False
                }
                disks.append(disk_info)
            except Exception as e:
                print(f"Error accediendo a {partition.device}: {e}")
                continue
    
    return disks

# --- RUTAS DE LA API LOCAL ---

@app.route('/status', methods=['GET'])
def status():
    """Estado del agente"""
    return jsonify({
        'success': True,
        'agent': AGENT_CONFIG,
        'system': get_system_info(),
        'timestamp': time.time()
    })

@app.route('/disks', methods=['GET'])
def list_disks():
    """Listar discos disponibles"""
    try:
        disks = list_available_disks()
        return jsonify({
            'success': True,
            'disks': disks,
            'count': len(disks)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

def bucle_principal(config):
    """Bucle principal del agente"""
    agente_id = config.get('agente_id', config.get('id', 'Unknown'))
    print(f"Agente iniciado con configuración: {agente_id}")
    
    # Iniciar servidor Flask local
    def start_server():
        app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)
    
    # Iniciar servidor en hilo separado
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Esperar a que el servidor esté listo
    time.sleep(2)
    
    # Abrir página web
    try:
        webbrowser.open('http://127.0.0.1:5001')
        print("Página web abierta en el navegador")
    except Exception as e:
        print(f"Error abriendo navegador: {e}")
    
    # Mantener el agente ejecutándose
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Agente detenido por el usuario")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente Forense de Adquisición")
    parser.add_argument("--server_url", help="URL del servidor principal para el registro inicial.")
    parser.add_argument("--token", help="Token de registro de un solo uso.")
    parser.add_argument("--install-startup", action="store_true", help="Solo configura el inicio automático y sale.")
    args = parser.parse_args()

    if args.install_startup:
        configurar_inicio_automatico()
        sys.exit(0)

    # Si se pasan los argumentos de registro, es el primer inicio
    if args.server_url and args.token:
        api_key, agente_id = registrar_con_token(args.server_url, args.token)
        if api_key and agente_id:
            guardar_configuracion(args.server_url, api_key, agente_id, args.token)
            AGENT_CONFIG.update({
                'id': agente_id,
                'server_url': args.server_url,
                'api_key': api_key,
                'token': args.token
            })
            
            # Configurar inicio automático
            configurar_inicio_automatico()
            
            # Iniciar el agente
            bucle_principal(AGENT_CONFIG)
        else:
            sys.exit(1)
    else:
        # Inicio normal (ejecutado por la Tarea Programada)
        try:
            with open(get_config_path(), 'r') as f:
                config = json.load(f)
            
            AGENT_CONFIG.update(config)
            print("Agente iniciado con configuración existente.")
            bucle_principal(AGENT_CONFIG)
        except FileNotFoundError:
            mostrar_error("El agente no está configurado. Por favor, reinstale usando el instalador de la plataforma web.")
            sys.exit(1)
