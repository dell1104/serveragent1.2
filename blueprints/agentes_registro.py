#!/usr/bin/env python3
"""
Blueprint para registro de agentes forenses
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import uuid
import time
from datetime import datetime

agentes_registro_bp = Blueprint('agentes_registro', __name__)

# Almacenamiento temporal de agentes (en producción usar BD)
AGENTES_REGISTRADOS = {}

@agentes_registro_bp.route('/api/agentes/registrar', methods=['POST'])
def registrar_agente():
    """Registra un nuevo agente forense"""
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No se recibieron datos'
            }), 400
        
        agente_id = data.get('agente_id')
        token = data.get('token')
        platform = data.get('platform', 'Unknown')
        python_version = data.get('python_version', 'Unknown')
        capabilities = data.get('capabilities', [])
        
        if not agente_id or not token:
            return jsonify({
                'success': False,
                'error': 'Faltan parámetros requeridos: agente_id, token'
            }), 400
        
        # Generar API key único
        api_key = str(uuid.uuid4())
        
        # Registrar agente
        AGENTES_REGISTRADOS[agente_id] = {
            'agente_id': agente_id,
            'api_key': api_key,
            'token': token,
            'platform': platform,
            'python_version': python_version,
            'capabilities': capabilities,
            'status': 'active',
            'registered_at': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'ip_address': request.remote_addr
        }
        
        current_app.logger.info(f"Agente registrado: {agente_id} desde {request.remote_addr}")
        
        return jsonify({
            'success': True,
            'api_key': api_key,
            'agente_id': agente_id,
            'message': 'Agente registrado exitosamente'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error registrando agente: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agentes_registro_bp.route('/api/agentes/status', methods=['GET'])
def obtener_estado_agentes():
    """Obtiene el estado de todos los agentes registrados"""
    try:
        return jsonify({
            'success': True,
            'agentes': list(AGENTES_REGISTRADOS.values()),
            'total': len(AGENTES_REGISTRADOS)
        })
    except Exception as e:
        current_app.logger.error(f"Error obteniendo estado de agentes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agentes_registro_bp.route('/api/agentes/<agente_id>/heartbeat', methods=['POST'])
def heartbeat_agente(agente_id):
    """Actualiza el heartbeat de un agente"""
    try:
        if agente_id not in AGENTES_REGISTRADOS:
            return jsonify({
                'success': False,
                'error': 'Agente no encontrado'
            }), 404
        
        # Actualizar último contacto
        AGENTES_REGISTRADOS[agente_id]['last_seen'] = datetime.now().isoformat()
        AGENTES_REGISTRADOS[agente_id]['ip_address'] = request.remote_addr
        
        return jsonify({
            'success': True,
            'message': 'Heartbeat actualizado'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error actualizando heartbeat: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agentes_registro_bp.route('/api/agentes/<agente_id>', methods=['GET'])
def obtener_agente(agente_id):
    """Obtiene información de un agente específico"""
    try:
        if agente_id not in AGENTES_REGISTRADOS:
            return jsonify({
                'success': False,
                'error': 'Agente no encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'agente': AGENTES_REGISTRADOS[agente_id]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo agente: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
