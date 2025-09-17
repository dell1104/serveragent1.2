# blueprints/user_panel.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Caso, ArchivoCaso, Usuario
from utils_package.logging_system import SistemaLogging
import datetime
import csv
import io

user_panel_bp = Blueprint('user_panel', __name__)

@user_panel_bp.route('/mi-panel')
@login_required
def mi_panel():
    """Panel personal del usuario"""
    return render_template('user_dashboard.html')

@user_panel_bp.route('/mi-configuracion')
@login_required
def mi_configuracion():
    """Configuración personal del usuario"""
    return render_template('user_config.html')

@user_panel_bp.route('/api/estadisticas-personales')
@login_required
def estadisticas_personales():
    """API para obtener estadísticas personales del usuario"""
    try:
        # Contar casos del usuario
        mis_casos = Caso.query.filter_by(usuario_id=current_user.id).count()
        casos_pendientes = Caso.query.filter_by(usuario_id=current_user.id, completado=False).count()
        casos_completados = Caso.query.filter_by(usuario_id=current_user.id, completado=True).count()
        
        # Contar archivos del usuario
        total_archivos = db.session.query(ArchivoCaso).join(Caso).filter(
            Caso.usuario_id == current_user.id
        ).count()
        
        return jsonify({
            'success': True,
            'estadisticas': {
                'mis_casos': mis_casos,
                'casos_pendientes': casos_pendientes,
                'casos_completados': casos_completados,
                'total_archivos': total_archivos
            }
        })
        
    except Exception as e:
        utils.log_evento("ERROR_ESTADISTICAS_PERSONALES", f"Error obteniendo estadísticas personales: {str(e)[:100]}")
        return jsonify({'success': False, 'error': str(e)}), 500

@user_panel_bp.route('/api/mis-casos-pendientes')
@login_required
def mis_casos_pendientes():
    """API para obtener casos pendientes del usuario"""
    try:
        casos = Caso.query.filter_by(
            usuario_id=current_user.id, 
            completado=False
        ).order_by(Caso.fecha_creacion.desc()).all()
        
        casos_data = []
        for caso in casos:
            casos_data.append({
                'id': caso.id,
                'expediente': caso.expediente,
                'origen_solicitud': caso.origen_solicitud,
                'tipo_requerimiento': caso.tipo_requerimiento,
                'fecha_creacion': caso.fecha_creacion.isoformat(),
                'estado_caso': caso.estado_caso,
                'completado': caso.completado
            })
        
        return jsonify({
            'success': True,
            'casos': casos_data
        })
        
    except Exception as e:
        print(f"Error obteniendo casos pendientes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@user_panel_bp.route('/api/todos-los-casos')
@login_required
def todos_los_casos():
    """API para obtener todos los casos (solo lectura para otros usuarios)"""
    try:
        casos = Caso.query.order_by(Caso.fecha_creacion.desc()).all()
        
        casos_data = []
        for caso in casos:
            casos_data.append({
                'id': caso.id,
                'expediente': caso.expediente,
                'origen_solicitud': caso.origen_solicitud,
                'tipo_requerimiento': caso.tipo_requerimiento,
                'fecha_creacion': caso.fecha_creacion.isoformat(),
                'estado_caso': caso.estado_caso,
                'completado': caso.completado,
                'usuario_id': caso.usuario_id,
                'usuario': {
                    'id': caso.usuario.id if caso.usuario else None,
                    'nombre_completo': caso.usuario.nombre_completo if caso.usuario else 'Sistema'
                } if caso.usuario else None
            })
        
        # Obtener tipos únicos para filtros
        tipos_requerimiento = db.session.query(Caso.tipo_requerimiento).filter(
            Caso.tipo_requerimiento.isnot(None)
        ).distinct().all()
        
        tipos = [t[0] for t in tipos_requerimiento if t[0]]
        
        return jsonify({
            'success': True,
            'casos': casos_data,
            'tipos_requerimiento': tipos
        })
        
    except Exception as e:
        print(f"Error obteniendo todos los casos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@user_panel_bp.route('/api/caso/<int:caso_id>')
@login_required
def obtener_caso(caso_id):
    """API para obtener detalles de un caso específico"""
    try:
        caso = Caso.query.get_or_404(caso_id)
        
        caso_data = {
            'id': caso.id,
            'expediente': caso.expediente,
            'origen_solicitud': caso.origen_solicitud,
            'tipo_requerimiento': caso.tipo_requerimiento,
            'fecha_creacion': caso.fecha_creacion.isoformat(),
            'fecha_actualizacion': caso.fecha_actualizacion.isoformat(),
            'estado_caso': caso.estado_caso,
            'completado': caso.completado,
            'observaciones': caso.observaciones,
            'fecha_intervencion': caso.fecha_intervencion.isoformat() if caso.fecha_intervencion else None,
            'hora_intervencion': caso.hora_intervencion.isoformat() if caso.hora_intervencion else None,
            'usuario_id': caso.usuario_id,
            'usuario': {
                'id': caso.usuario.id if caso.usuario else None,
                'nombre_completo': caso.usuario.nombre_completo if caso.usuario else 'Sistema'
            } if caso.usuario else None
        }
        
        return jsonify({
            'success': True,
            'caso': caso_data
        })
        
    except Exception as e:
        print(f"Error obteniendo caso: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@user_panel_bp.route('/api/caso/<int:caso_id>', methods=['PUT'])
@login_required
def actualizar_caso(caso_id):
    """API para actualizar un caso (solo propios)"""
    try:
        caso = Caso.query.get_or_404(caso_id)
        
        # Verificar que el usuario es el propietario del caso
        if caso.usuario_id != current_user.id:
            return jsonify({'success': False, 'error': 'No tienes permisos para editar este caso'}), 403
        
        data = request.get_json()
        
        # Actualizar campos permitidos
        if 'origen_solicitud' in data:
            caso.origen_solicitud = data['origen_solicitud']
        if 'tipo_requerimiento' in data:
            caso.tipo_requerimiento = data['tipo_requerimiento']
        if 'estado_caso' in data:
            caso.estado_caso = data['estado_caso']
            # Actualizar campo completado basado en el estado
            caso.completado = data['estado_caso'] == 'Completado'
        if 'observaciones' in data:
            caso.observaciones = data['observaciones']
        
        caso.fecha_actualizacion = datetime.datetime.utcnow()
        
        db.session.commit()
        
        # Log del evento
        SistemaLogging.log_case_update(current_user.username, caso_id, {
            'origen_solicitud': data.get('origen_solicitud'),
            'tipo_requerimiento': data.get('tipo_requerimiento'),
            'estado_caso': data.get('estado_caso'),
            'observaciones': data.get('observaciones')
        })
        
        return jsonify({
            'success': True,
            'mensaje': 'Caso actualizado correctamente'
        })
        
    except Exception as e:
        print(f"Error actualizando caso: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@user_panel_bp.route('/api/mi-perfil', methods=['PUT'])
@login_required
def actualizar_perfil():
    """API para actualizar perfil del usuario"""
    try:
        data = request.get_json()
        
        # Actualizar campos permitidos
        if 'nombre_completo' in data:
            current_user.nombre_completo = data['nombre_completo']
        if 'email' in data:
            # Verificar que el email no esté en uso por otro usuario
            existing_user = Usuario.query.filter_by(email=data['email']).first()
            if existing_user and existing_user.id != current_user.id:
                return jsonify({'success': False, 'error': 'El email ya está en uso'}), 400
            current_user.email = data['email']
        if 'assemblyai_key' in data:
            current_user.assemblyai_key = data['assemblyai_key']
        
        db.session.commit()
        
        # Log del evento
        SistemaLogging.log_user_update(current_user.username, current_user.id, {
            'nombre_completo': data.get('nombre_completo'),
            'email': data.get('email'),
            'assemblyai_key_updated': 'assemblyai_key' in data
        })
        
        return jsonify({
            'success': True,
            'mensaje': 'Perfil actualizado correctamente'
        })
        
    except Exception as e:
        print(f"Error actualizando perfil: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@user_panel_bp.route('/api/cambiar-password', methods=['POST'])
@login_required
def cambiar_password():
    """API para cambiar contraseña del usuario"""
    try:
        data = request.get_json()
        password_actual = data.get('password_actual')
        password_nueva = data.get('password_nueva')
        
        if not password_actual or not password_nueva:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400
        
        # Verificar contraseña actual
        if not current_user.check_password(password_actual):
            return jsonify({'success': False, 'error': 'Contraseña actual incorrecta'}), 400
        
        # Cambiar contraseña
        current_user.set_password(password_nueva)
        db.session.commit()
        
        # Log del evento
        SistemaLogging.log_evento(
            'PASSWORD_CHANGE',
            f'Usuario {current_user.username} cambió su contraseña',
            'AUTH',
            {'usuario_id': current_user.id}
        )
        
        return jsonify({
            'success': True,
            'mensaje': 'Contraseña cambiada correctamente'
        })
        
    except Exception as e:
        print(f"Error cambiando contraseña: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@user_panel_bp.route('/api/exportar-mis-casos')
@login_required
def exportar_mis_casos():
    """API para exportar casos del usuario a CSV"""
    try:
        casos = Caso.query.filter_by(usuario_id=current_user.id).order_by(Caso.fecha_creacion.desc()).all()
        
        # Crear CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Encabezados
        writer.writerow([
            'ID', 'Expediente', 'Origen Solicitud', 'Tipo Requerimiento',
            'Estado', 'Completado', 'Fecha Creación', 'Fecha Actualización',
            'Observaciones'
        ])
        
        # Datos
        for caso in casos:
            writer.writerow([
                caso.id,
                caso.expediente,
                caso.origen_solicitud or '',
                caso.tipo_requerimiento or '',
                caso.estado_caso,
                'Sí' if caso.completado else 'No',
                caso.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S'),
                caso.fecha_actualizacion.strftime('%Y-%m-%d %H:%M:%S'),
                caso.observaciones or ''
            ])
        
        # Preparar respuesta
        output.seek(0)
        filename = f"mis_casos_{current_user.username}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return jsonify({
            'success': True,
            'filename': filename,
            'content': output.getvalue(),
            'total_registros': len(casos)
        })
        
    except Exception as e:
        print(f"Error exportando casos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@user_panel_bp.route('/api/mi-actividad')
@login_required
def mi_actividad():
    """API para obtener actividad reciente del usuario"""
    try:
        from models import LogEvento
        
        # Obtener logs del usuario de los últimos 30 días
        fecha_limite = datetime.datetime.now() - datetime.timedelta(days=30)
        
        logs = LogEvento.query.filter(
            LogEvento.usuario_id == current_user.id,
            LogEvento.fecha_evento >= fecha_limite
        ).order_by(LogEvento.fecha_evento.desc()).limit(20).all()
        
        actividad_data = []
        for log in logs:
            actividad_data.append({
                'id': log.id,
                'tipo_evento': log.tipo_evento,
                'descripcion': log.descripcion,
                'fecha_evento': log.fecha_evento.isoformat(),
                'ip_address': log.ip_address
            })
        
        return jsonify({
            'success': True,
            'actividad': actividad_data
        })
        
    except Exception as e:
        print(f"Error obteniendo actividad: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
