#!/usr/bin/env python3
"""
Agente Forense - Stack con Python 3.9
Comunicación con el sistema principal para adquisición forense
"""

import os
import sys
import json
import time
import uuid
import hashlib
import subprocess
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import psutil
import magic

app = Flask(__name__)
CORS(app)

# Configuración del agente
AGENT_CONFIG = {
    'id': os.getenv('AGENT_ID', 'forensic_agent_001'),
    'name': os.getenv('AGENT_NAME', 'Agente Forense Principal'),
    'version': '1.0.0',
    'python_version': '3.9',
    'capabilities': ['DD', 'E01', 'AFF4'],
    'max_concurrent_operations': 2
}

# Almacenamiento de operaciones activas
ACTIVE_OPERATIONS = {}

# Directorios de trabajo
FORENSIC_DATA_DIR = '/app/forensic_data'
TEMP_DIR = '/app/temp'
LOGS_DIR = '/app/logs'

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
    """Obtener información del sistema"""
    return {
        'hostname': os.uname().nodename,
        'platform': os.uname().sysname,
        'architecture': os.uname().machine,
        'python_version': sys.version,
        'memory_total': psutil.virtual_memory().total,
        'memory_available': psutil.virtual_memory().available,
        'disk_usage': psutil.disk_usage('/').percent,
        'cpu_count': psutil.cpu_count(),
        'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
    }

def list_available_disks():
    """Listar discos disponibles en el sistema"""
    disks = []
    
    # Obtener particiones de disco
    partitions = psutil.disk_partitions()
    
    for partition in partitions:
        try:
            # Obtener información de uso
            usage = psutil.disk_usage(partition.mountpoint)
            
            disk_info = {
                'device': partition.device,
                'mountpoint': partition.mountpoint,
                'fstype': partition.fstype,
                'total_size': usage.total,
                'used_size': usage.used,
                'free_size': usage.free,
                'readable': os.access(partition.mountpoint, os.R_OK),
                'writable': os.access(partition.mountpoint, os.W_OK)
            }
            
            # Verificar si es un dispositivo de bloque (disco físico)
            if partition.device.startswith('/dev/'):
                disk_info['is_physical'] = True
                disk_info['device_id'] = partition.device
            else:
                disk_info['is_physical'] = False
            
            disks.append(disk_info)
            
        except (PermissionError, OSError) as e:
            log_operation('system', f"Error accediendo a {partition.device}: {e}", 'WARNING')
            continue
    
    # Agregar discos simulados para demostración
    # En un entorno real, estos vendrían de una API o configuración
    simulated_disks = [
        {
            'device': 'C:',
            'mountpoint': 'C:\\',
            'fstype': 'NTFS',
            'total_size': 1000000000000,  # 1TB
            'used_size': 500000000000,    # 500GB
            'free_size': 500000000000,    # 500GB
            'readable': True,
            'writable': False,
            'is_physical': True,
            'device_id': 'C:',
            'model': 'Disco Principal C: (1TB) (HDD)',
            'size_gb': 1000,
            'size_human': '1 TB'
        },
        {
            'device': 'D:',
            'mountpoint': 'D:\\',
            'fstype': 'NTFS',
            'total_size': 500000000000,   # 500GB
            'used_size': 200000000000,    # 200GB
            'free_size': 300000000000,    # 300GB
            'readable': True,
            'writable': False,
            'is_physical': True,
            'device_id': 'D:',
            'model': 'Disco D: (500GB) (SSD)',
            'size_gb': 500,
            'size_human': '500 GB'
        },
        {
            'device': 'E:',
            'mountpoint': 'E:\\',
            'fstype': 'FAT32',
            'total_size': 32000000000,    # 32GB
            'used_size': 10000000000,     # 10GB
            'free_size': 22000000000,     # 22GB
            'readable': True,
            'writable': False,
            'is_physical': True,
            'device_id': 'E:',
            'model': 'USB Kingston (32GB) (USB)',
            'size_gb': 32,
            'size_human': '32 GB'
        }
    ]
    
    # Agregar discos simulados
    disks.extend(simulated_disks)
    
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
    """Adquirir disco usando dd"""
    try:
        log_operation(operation_id, f"Iniciando adquisición DD de {device_id}")
        
        # Comando dd
        cmd = [
            'dd',
            f'if={device_id}',
            f'of={output_path}',
            'bs=1M',
            'status=progress'
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
            # Calcular hashes
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
            raise Exception(f"Error en dd: {stderr}")
            
    except Exception as e:
        log_operation(operation_id, f"Error en adquisición DD: {e}", 'ERROR')
        ACTIVE_OPERATIONS[operation_id].update({
            'status': 'error',
            'success': False,
            'error': str(e),
            'end_time': datetime.now().isoformat()
        })
        return False

def acquire_disk_ewf(device_id, output_path, operation_id):
    """Adquirir disco usando EWF con ewfacquire"""
    try:
        log_operation(operation_id, f"Iniciando adquisición EWF de {device_id}")
        
        # Verificar que ewfacquire esté disponible
        try:
            subprocess.run(['ewfacquire', '--version'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise Exception("ewfacquire no está instalado o no está disponible")
        
        # Comando ewfacquire
        cmd = [
            'ewfacquire',
            '-t', output_path,
            '-f', 'encase6',  # Formato EnCase 6
            '-c', 'best',     # Compresión máxima
            '-e', 'Agente Forense',  # Examinador
            '-E', 'Sistema Forense',  # Evidencia
            '-D', 'Adquisición automática',  # Descripción
            '-N', 'Adquisición desde agente forense',  # Notas
            '-C', 'Caso Forense',  # Caso
            '-m', 'fixed',    # Tipo de medio fijo
            '-S', '1.4',      # Tamaño de segmento en GB
            '-u',             # Modo no interactivo
            device_id
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
            # Buscar archivos generados
            output_files = []
            for file in os.listdir(os.path.dirname(output_path)):
                if file.startswith(os.path.basename(output_path)):
                    output_files.append(os.path.join(os.path.dirname(output_path), file))
            
            # Calcular hashes
            total_size = sum(os.path.getsize(f) for f in output_files)
            file_hashes = {f: calculate_file_hash(f) for f in output_files}
            
            ACTIVE_OPERATIONS[operation_id].update({
                'status': 'completed',
                'success': True,
                'file_size': total_size,
                'file_hashes': file_hashes,
                'output_files': output_files,
                'end_time': datetime.now().isoformat()
            })
            
            log_operation(operation_id, f"Adquisición EWF completada: {total_size} bytes")
            return True
        else:
            raise Exception(f"Error en ewfacquire: {stderr}")
            
    except Exception as e:
        log_operation(operation_id, f"Error en adquisición EWF: {e}", 'ERROR')
        ACTIVE_OPERATIONS[operation_id].update({
            'status': 'error',
            'success': False,
            'error': str(e),
            'end_time': datetime.now().isoformat()
        })
        return False

def acquire_disk_aff4(device_id, output_path, operation_id):
    """Adquirir disco usando AFF4 con affacquire"""
    try:
        log_operation(operation_id, f"Iniciando adquisición AFF4 de {device_id}")
        
        # Verificar que affacquire esté disponible
        try:
            subprocess.run(['affacquire', '--version'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise Exception("affacquire no está instalado o no está disponible")
        
        # Comando affacquire
        cmd = [
            'affacquire',
            '-i', device_id,
            '-o', output_path,
            '-c', 'best',  # Compresión máxima
            '-d', 'Agente Forense',  # Descripción
            '-e', 'Sistema Forense',  # Examinador
            '-n', 'Adquisición automática'  # Notas
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
            # Calcular hashes
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
            
            log_operation(operation_id, f"Adquisición AFF4 completada: {file_size} bytes")
            return True
        else:
            raise Exception(f"Error en affacquire: {stderr}")
            
    except Exception as e:
        log_operation(operation_id, f"Error en adquisición AFF4: {e}", 'ERROR')
        ACTIVE_OPERATIONS[operation_id].update({
            'status': 'error',
            'success': False,
            'error': str(e),
            'end_time': datetime.now().isoformat()
        })
        return False

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
        if format_type == 'E01':
            output_path = os.path.join(output_dir, f"{output_name}.E01")
        elif format_type == 'AFF4':
            output_path = os.path.join(output_dir, f"{output_name}.aff4")
        else:  # DD
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
                acquire_disk_dd(device_id, output_path, operation_id)
            elif format_type == 'E01':
                acquire_disk_ewf(device_id, output_path, operation_id)
            elif format_type == 'AFF4':
                acquire_disk_aff4(device_id, output_path, operation_id)
        
        thread = threading.Thread(target=acquisition_thread)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'operation_id': operation_id,
            'message': 'Adquisición iniciada'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/acquire/<operation_id>/status', methods=['GET'])
def get_operation_status(operation_id):
    """Obtener estado de una operación"""
    if operation_id not in ACTIVE_OPERATIONS:
        return jsonify({
            'success': False,
            'error': 'Operación no encontrada'
        }), 404
    
    operation = ACTIVE_OPERATIONS[operation_id]
    
    return jsonify({
        'success': True,
        'operation': operation
    })

@app.route('/acquire/<operation_id>/cancel', methods=['POST'])
def cancel_operation(operation_id):
    """Cancelar operación"""
    if operation_id not in ACTIVE_OPERATIONS:
        return jsonify({
            'success': False,
            'error': 'Operación no encontrada'
        }), 404
    
    ACTIVE_OPERATIONS[operation_id].update({
        'status': 'cancelled',
        'end_time': datetime.now().isoformat()
    })
    
    return jsonify({
        'success': True,
        'message': 'Operación cancelada'
    })

@app.route('/operations', methods=['GET'])
def list_operations():
    """Listar todas las operaciones"""
    return jsonify({
        'success': True,
        'operations': list(ACTIVE_OPERATIONS.values())
    })

if __name__ == '__main__':
    # Crear directorios necesarios
    ensure_directories()
    
    # Log de inicio
    log_operation('system', f"Iniciando agente forense: {AGENT_CONFIG['name']}")
    
    # Iniciar aplicación
    app.run(host='0.0.0.0', port=5001, debug=False)