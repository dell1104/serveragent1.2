#!/usr/bin/env python3
"""
Agente Forense Windows Local
Se ejecuta en la máquina Windows del usuario para acceder a discos locales
"""

import os
import sys
import json
import time
import uuid
import hashlib
import subprocess
import threading
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import psutil
import wmi

app = Flask(__name__)
CORS(app)

# Configuración del agente
AGENT_CONFIG = {
    'id': 'forensic_agent_windows_local',
    'name': 'Agente Forense Windows Local',
    'version': '1.0.0',
    'python_version': '3.13',
    'capabilities': ['DD', 'E01', 'AFF4'],
    'max_concurrent_operations': 2,
    'server_url': 'http://192.168.1.93:5000'  # URL del servidor principal
}

# Almacenamiento de operaciones activas
ACTIVE_OPERATIONS = {}

# Directorios de trabajo
FORENSIC_DATA_DIR = os.path.join(os.getcwd(), 'forensic_data')
TEMP_DIR = os.path.join(os.getcwd(), 'temp')
LOGS_DIR = os.path.join(os.getcwd(), 'logs')

def ensure_directories():
    """Crear directorios necesarios si no existen"""
    for directory in [FORENSIC_DATA_DIR, TEMP_DIR, LOGS_DIR]:
        os.makedirs(directory, exist_ok=True)

def log_operation(operation_id, message, level='INFO'):
    """Registrar evento de operación"""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{level}] [{operation_id}] {message}\n"
    
    log_file = os.path.join(LOGS_DIR, f"agent_{AGENT_CONFIG['id']}.log")
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    
    print(log_entry.strip())

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
        log_operation('system', f"Error obteniendo info del sistema: {e}", 'ERROR')
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
        
        # Obtener discos físicos
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
                    'readable': True,  # Asumimos que es legible
                    'writable': False  # No escribimos en discos físicos para forensia
                }
                
                # Agregar información de tamaño legible
                if disk.Size:
                    size_gb = disk.Size / (1024**3)
                    disk_info['size_gb'] = round(size_gb, 2)
                    disk_info['size_human'] = f"{disk_info['size_gb']} GB"
                
                disks.append(disk_info)
                
            except Exception as e:
                log_operation('disk', f"Error procesando disco {disk.DeviceID}: {e}", 'WARNING')
                continue
                
    except Exception as e:
        log_operation('disk', f"Error obteniendo discos: {e}", 'ERROR')
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
                log_operation('disk', f"Error accediendo a {partition.device}: {e}", 'WARNING')
                continue
    
    return disks

def calculate_file_hash(file_path, algorithm='sha256'):
    """Calcular hash de un archivo"""
    hash_obj = hashlib.new(algorithm)
    
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        log_operation('hash', f"Error calculando hash de {file_path}: {e}", 'ERROR')
        return None

def acquire_disk_dd(device_id, output_path, operation_id):
    """Adquirir disco usando dd (si está disponible) o alternativa Windows"""
    try:
        log_operation(operation_id, f"Iniciando adquisición DD de {device_id}")
        
        # En Windows, usar PowerShell para copiar el disco
        cmd = [
            'powershell',
            '-Command',
            f'Copy-Item -Path "{device_id}" -Destination "{output_path}" -Force'
        ]
        
        # Ejecutar comando
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Monitorear progreso
        while process.poll() is None:
            time.sleep(1)
            
            # Actualizar estado de la operación
            if operation_id in ACTIVE_OPERATIONS:
                ACTIVE_OPERATIONS[operation_id]['status'] = 'in_progress'
                ACTIVE_OPERATIONS[operation_id]['last_update'] = datetime.now().isoformat()
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            # Calcular hash
            file_size = os.path.getsize(output_path)
            file_hash = calculate_file_hash(output_path)
            
            ACTIVE_OPERATIONS[operation_id].update({
                'status': 'completed',
                'success': True,
                'file_size': file_size,
                'file_hash': file_hash,
                'end_time': datetime.now().isoformat(),
                'output_file': output_path
            })
            
            log_operation(operation_id, f"Adquisición DD completada: {file_size} bytes")
            return True
        else:
            raise Exception(f"Error en PowerShell: {stderr}")
            
    except Exception as e:
        log_operation(operation_id, f"Error en adquisición DD: {e}", 'ERROR')
        ACTIVE_OPERATIONS[operation_id].update({
            'status': 'error',
            'success': False,
            'error': str(e),
            'end_time': datetime.now().isoformat()
        })
        return False

def send_to_server(operation_data):
    """Enviar datos de operación al servidor principal"""
    try:
        response = requests.post(
            f"{AGENT_CONFIG['server_url']}/api/forensic/operation",
            json=operation_data,
            timeout=30
        )
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        log_operation('server', f"Error enviando datos al servidor: {e}", 'ERROR')
        return None

# Rutas de la API

@app.route('/status', methods=['GET'])
def status():
    """Estado del agente"""
    return jsonify({
        'success': True,
        'agent': AGENT_CONFIG,
        'system': get_system_info(),
        'active_operations': len(ACTIVE_OPERATIONS),
        'timestamp': datetime.now().isoformat()
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

@app.route('/acquire', methods=['POST'])
def start_acquisition():
    """Iniciar adquisición forense"""
    try:
        data = request.json
        device_id = data.get('device_id')
        format_type = data.get('format', 'DD')
        output_name = data.get('output_name')
        case_id = data.get('case_id')
        
        if not all([device_id, output_name, case_id]):
            return jsonify({
                'success': False,
                'error': 'Faltan parámetros requeridos'
            }), 400
        
        # Verificar que el formato sea soportado
        if format_type not in AGENT_CONFIG['capabilities']:
            return jsonify({
                'success': False,
                'error': f'Formato {format_type} no soportado'
            }), 400
        
        # Generar ID de operación
        operation_id = str(uuid.uuid4())
        
        # Crear directorio de salida
        output_dir = os.path.join(FORENSIC_DATA_DIR, case_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Ruta de salida
        output_path = os.path.join(output_dir, f"{output_name}.dd")
        
        # Registrar operación
        ACTIVE_OPERATIONS[operation_id] = {
            'operation_id': operation_id,
            'device_id': device_id,
            'format': format_type,
            'output_name': output_name,
            'case_id': case_id,
            'output_path': output_path,
            'status': 'starting',
            'start_time': datetime.now().isoformat(),
            'progress': 0
        }
        
        # Iniciar adquisición en hilo separado
        def acquisition_thread():
            if format_type == 'DD':
                success = acquire_disk_dd(device_id, output_path, operation_id)
            
            # Enviar resultado al servidor
            send_to_server(ACTIVE_OPERATIONS[operation_id])
        
        thread = threading.Thread(target=acquisition_thread)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'operation_id': operation_id,
            'message': 'Adquisición iniciada'
        })
        
    except Exception as e:
        log_operation('api', f"Error en start_acquisition: {e}", 'ERROR')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/operation/<operation_id>', methods=['GET'])
def get_operation_status(operation_id):
    """Obtener estado de una operación"""
    if operation_id not in ACTIVE_OPERATIONS:
        return jsonify({
            'success': False,
            'error': 'Operación no encontrada'
        }), 404
    
    return jsonify({
        'success': True,
        'operation': ACTIVE_OPERATIONS[operation_id]
    })

@app.route('/operations', methods=['GET'])
def list_operations():
    """Listar todas las operaciones"""
    return jsonify({
        'success': True,
        'operations': list(ACTIVE_OPERATIONS.values())
    })

if __name__ == '__main__':
    ensure_directories()
    log_operation('startup', f"Iniciando agente forense: {AGENT_CONFIG['name']}")
    
    print(f"Agente Forense Windows Local iniciado")
    print(f"Accesible en: http://localhost:5001")
    print(f"Servidor principal: {AGENT_CONFIG['server_url']}")
    
    app.run(host='0.0.0.0', port=5001, debug=False)
