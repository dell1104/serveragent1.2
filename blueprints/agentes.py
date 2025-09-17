"""
Blueprint para gestión de agentes forenses
Maneja la comunicación con agentes (usuarios) remotos
"""

import requests
import json
import time
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models import db, Usuario, OperacionForense
import utils

agentes_bp = Blueprint('agentes', __name__)

# Cache de operaciones en progreso (temporal hasta migrar a BD)
OPERACIONES_ACTIVAS = {}

def get_agent_by_id(agent_id):
    """Obtiene un agente por su ID"""
    return Usuario.query.filter_by(agente_id=agent_id, es_agente=True).first()

def get_agent_url(agent_id):
    """Obtiene la URL completa del agente"""
    agente = get_agent_by_id(agent_id)
    if not agente:
        return None
    return agente.get_agent_url()

def get_agent_headers(agent_id):
    """Obtiene los headers de autenticación para el agente"""
    agente = get_agent_by_id(agent_id)
    if not agente or not agente.api_key:
        return {}
    return {'Authorization': f"Bearer {agente.api_key}"}

def check_agent_status(agent_id):
    """Verifica el estado de un agente"""
    try:
        agente = get_agent_by_id(agent_id)
        if not agente:
            return False
            
        url = get_agent_url(agent_id)
        headers = get_agent_headers(agent_id)
        
        if not url:
            return False
        
        response = requests.get(f"{url}/status", headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            agente.update_agent_status('online', version=data.get('agent', {}).get('version'))
            db.session.commit()
            return True
        else:
            agente.update_agent_status('offline')
            db.session.commit()
            return False
            
    except Exception as e:
        # Log del error pero no lo imprimimos en consola para evitar spam
        utils.log_evento(f"AGENTE_OFFLINE", f"Agente {agent_id} no disponible: {str(e)[:100]}")
        agente = get_agent_by_id(agent_id)
        if agente:
            agente.update_agent_status('offline')
            db.session.commit()
        return False

@agentes_bp.route('/api/agentes', methods=['GET'])
@login_required
def listar_agentes():
    """Lista todos los agentes registrados"""
    try:
        # Obtener todos los usuarios que son agentes
        agentes = Usuario.query.filter_by(es_agente=True).all()
        
        # Verificar estado de todos los agentes
        for agente in agentes:
            if agente.agente_id:
                check_agent_status(agente.agente_id)
        
        agentes_list = []
        for agente in agentes:
            if agente.agente_id:  # Solo incluir agentes con ID válido
                agentes_list.append({
                    'id': agente.agente_id,
                    'name': f"{agente.nombre_completo} ({agente.username})",
                    'ip': agente.ip_agente,
                    'port': agente.puerto_agente,
                    'status': agente.estado_agente,
                    'last_seen': agente.ultima_conexion.isoformat() if agente.ultima_conexion else None,
                    'capabilities': agente.capacidades_forenses or [],
                    'location': agente.ubicacion_agente,
                    'os': agente.sistema_operativo,
                    'version': agente.version_agente,
                    'max_operations': agente.max_operaciones_concurrentes,
                    'user_id': agente.id
                })
        
        return jsonify({
            'success': True,
            'agentes': agentes_list,
            'total': len(agentes_list)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agentes_bp.route('/api/agentes/<agent_id>/discos', methods=['GET'])
@login_required
def listar_discos_agente(agent_id):
    """Lista los discos de un agente específico"""
    try:
        agente = get_agent_by_id(agent_id)
        if not agente:
            return jsonify({'success': False, 'error': 'Agente no encontrado'}), 404
        
        # Verificar que el agente esté online
        if not check_agent_status(agent_id):
            return jsonify({'success': False, 'error': 'Agente offline'}), 503
        
        url = get_agent_url(agent_id)
        headers = get_agent_headers(agent_id)
        
        response = requests.get(f"{url}/disks", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
        else:
            return jsonify({'success': False, 'error': 'Error comunicándose con el agente'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agentes_bp.route('/api/agentes/<agent_id>/adquirir', methods=['POST'])
@login_required
def iniciar_adquisicion(agent_id):
    """Inicia una adquisición en un agente específico"""
    try:
        agente = get_agent_by_id(agent_id)
        if not agente:
            return jsonify({'success': False, 'error': 'Agente no encontrado'}), 404
        
        # Verificar que el agente esté online
        if not check_agent_status(agent_id):
            return jsonify({'success': False, 'error': 'Agente offline'}), 503
        
        data = request.json
        device_id = data.get('device_id')
        format_type = data.get('format', 'DD')
        output_name = data.get('output_name')
        case_id = data.get('case_id')
        
        if not all([device_id, format_type, output_name, case_id]):
            return jsonify({'success': False, 'error': 'Faltan parámetros requeridos'}), 400
        
        # Verificar que el formato sea soportado
        if not agente.has_capability(format_type):
            return jsonify({'success': False, 'error': f'Formato {format_type} no soportado por este agente'}), 400
        
        url = get_agent_url(agent_id)
        headers = get_agent_headers(agent_id)
        
        # Datos para enviar al agente
        agent_data = {
            'device_id': device_id,
            'format': format_type,
            'output_name': output_name,
            'case_id': case_id
        }
        
        response = requests.post(f"{url}/acquire", json=agent_data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Registrar la operación en la base de datos
            operation_id = data.get('operation_id')
            if operation_id:
                operacion = OperacionForense(
                    operation_id=operation_id,
                    caso_id=case_id,
                    dispositivo_id=device_id,
                    formato_adquisicion=format_type,
                    nombre_archivo=output_name,
                    estado='iniciando',
                    usuario_agente_id=agente.id
                )
                
                db.session.add(operacion)
                db.session.commit()
                
                # También mantener en cache temporal
                OPERACIONES_ACTIVAS[operation_id] = {
                    'agent_id': agent_id,
                    'case_id': case_id,
                    'device_id': device_id,
                    'format': format_type,
                    'output_name': output_name,
                    'start_time': datetime.now().isoformat(),
                    'status': 'in_progress',
                    'user_id': current_user.id
                }
                
                # Log de la operación
                utils.SistemaLogging.log_forensic_acquisition(
                    user_id=current_user.id,
                    device=device_id,
                    destination=f"Agente {agent_id}",
                    format=format_type,
                    command=f"Adquisición remota en {agente.nombre_completo}"
                )
            
            return jsonify(data)
        else:
            return jsonify({'success': False, 'error': 'Error comunicándose con el agente'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agentes_bp.route('/api/agentes/<agent_id>/operacion/<operation_id>/estado', methods=['GET'])
@login_required
def obtener_estado_operacion(agent_id, operation_id):
    """Obtiene el estado de una operación en progreso"""
    try:
        if agent_id not in AGENTES_REGISTRADOS:
            return jsonify({'success': False, 'error': 'Agente no encontrado'}), 404
        
        if operation_id not in OPERACIONES_ACTIVAS:
            return jsonify({'success': False, 'error': 'Operación no encontrada'}), 404
        
        # Verificar que el agente esté online
        if not check_agent_status(agent_id):
            return jsonify({'success': False, 'error': 'Agente offline'}), 503
        
        url = get_agent_url(agent_id)
        headers = get_agent_headers(agent_id)
        
        response = requests.get(f"{url}/acquire/{operation_id}/status", headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # Actualizar estado local
            if data.get('operation'):
                operation = data['operation']
                OPERACIONES_ACTIVAS[operation_id].update({
                    'status': 'completed' if operation.get('success') else 'error',
                    'progress': data.get('progress', 0),
                    'end_time': operation.get('end_time'),
                    'file_size': operation.get('file_size'),
                    'hashes': operation.get('hashes', {}),
                    'error': operation.get('error')
                })
            
            return jsonify(data)
        else:
            return jsonify({'success': False, 'error': 'Error comunicándose con el agente'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agentes_bp.route('/api/agentes/<agent_id>/operacion/<operation_id>/cancelar', methods=['POST'])
@login_required
def cancelar_operacion(agent_id, operation_id):
    """Cancela una operación en progreso"""
    try:
        if agent_id not in AGENTES_REGISTRADOS:
            return jsonify({'success': False, 'error': 'Agente no encontrado'}), 404
        
        if operation_id not in OPERACIONES_ACTIVAS:
            return jsonify({'success': False, 'error': 'Operación no encontrada'}), 404
        
        # Verificar que el agente esté online
        if not check_agent_status(agent_id):
            return jsonify({'success': False, 'error': 'Agente offline'}), 503
        
        url = get_agent_url(agent_id)
        headers = get_agent_headers(agent_id)
        
        response = requests.post(f"{url}/acquire/{operation_id}/cancel", headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Actualizar estado local
            OPERACIONES_ACTIVAS[operation_id]['status'] = 'cancelled'
            OPERACIONES_ACTIVAS[operation_id]['end_time'] = datetime.now().isoformat()
            
            return jsonify({'success': True, 'message': 'Operación cancelada'})
        else:
            return jsonify({'success': False, 'error': 'Error comunicándose con el agente'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agentes_bp.route('/api/operaciones', methods=['GET'])
@login_required
def listar_operaciones():
    """Lista todas las operaciones activas"""
    try:
        operaciones_list = []
        for operation_id, operacion in OPERACIONES_ACTIVAS.items():
            operaciones_list.append({
                'operation_id': operation_id,
                'agent_id': operacion['agent_id'],
                'agent_name': AGENTES_REGISTRADOS[operacion['agent_id']]['name'],
                'case_id': operacion['case_id'],
                'device_id': operacion['device_id'],
                'format': operacion['format'],
                'output_name': operacion['output_name'],
                'start_time': operacion['start_time'],
                'end_time': operacion.get('end_time'),
                'status': operacion['status'],
                'progress': operacion.get('progress', 0),
                'file_size': operacion.get('file_size'),
                'hashes': operacion.get('hashes', {}),
                'error': operacion.get('error'),
                'user_id': operacion['user_id']
            })
        
        return jsonify({
            'success': True,
            'operaciones': operaciones_list,
            'total': len(operaciones_list)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agentes_bp.route('/api/usuarios/<user_id>/convertir-agente', methods=['POST'])
@login_required
def convertir_usuario_agente(user_id):
    """Convierte un usuario en agente forense"""
    try:
        # Solo administradores pueden convertir usuarios en agentes
        if not current_user.is_admin():
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
        
        if usuario.is_agent():
            return jsonify({'success': False, 'error': 'El usuario ya es un agente'}), 400
        
        data = request.json
        ip_agente = data.get('ip_agente')
        puerto_agente = data.get('puerto_agente', 5001)
        ubicacion = data.get('ubicacion', 'Desconocida')
        sistema_operativo = data.get('sistema_operativo', 'Windows')
        capacidades = data.get('capacidades', ['DD', 'E01', 'AFF4'])
        max_operaciones = data.get('max_operaciones', 1)
        
        if not ip_agente:
            return jsonify({'success': False, 'error': 'IP del agente es requerida'}), 400
        
        # Convertir usuario en agente
        usuario.es_agente = True
        usuario.generate_agent_id()
        usuario.generate_api_key()
        usuario.ip_agente = ip_agente
        usuario.puerto_agente = puerto_agente
        usuario.ubicacion_agente = ubicacion
        usuario.sistema_operativo = sistema_operativo
        usuario.set_agent_capabilities(capacidades)
        usuario.max_operaciones_concurrentes = max_operaciones
        usuario.estado_agente = 'offline'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Usuario convertido en agente correctamente',
            'agente': {
                'id': usuario.agente_id,
                'name': f"{usuario.nombre_completo} ({usuario.username})",
                'ip': usuario.ip_agente,
                'port': usuario.puerto_agente,
                'api_key': usuario.api_key,
                'location': usuario.ubicacion_agente,
                'os': usuario.sistema_operativo,
                'capabilities': usuario.capacidades_forenses,
                'max_operations': usuario.max_operaciones_concurrentes
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@agentes_bp.route('/api/agentes/<agent_id>/desactivar', methods=['POST'])
@login_required
def desactivar_agente(agent_id):
    """Desactiva un agente (convierte de vuelta a usuario normal)"""
    try:
        # Solo administradores pueden desactivar agentes
        if not current_user.is_admin():
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        
        agente = get_agent_by_id(agent_id)
        if not agente:
            return jsonify({'success': False, 'error': 'Agente no encontrado'}), 404
        
        # Desactivar agente
        agente.es_agente = False
        agente.estado_agente = 'offline'
        agente.agente_id = None
        agente.api_key = None
        agente.ip_agente = None
        agente.puerto_agente = None
        agente.ubicacion_agente = None
        agente.sistema_operativo = None
        agente.capacidades_forenses = None
        agente.max_operaciones_concurrentes = None
        agente.ultima_conexion = None
        agente.version_agente = None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Agente desactivado correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
