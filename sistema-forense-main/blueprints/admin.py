# blueprints/admin.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Usuario, Caso, LogEvento, ArchivoCaso
from utils_package.logging_system import SistemaLogging
import bcrypt
import datetime
import os

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorador para requerir permisos de administrador"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            # Si es una petición AJAX, devolver JSON
            if request.headers.get('Content-Type') == 'application/json' or request.headers.get('Accept') == 'application/json':
                return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
            # Si es una petición normal, mostrar página de error
            return render_template('error_403.html'), 403
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/admin-panel')
@login_required
@admin_required
def admin_panel():
    """Panel de administración"""
    return render_template('admin_panel.html')

@admin_bp.route('/api/usuarios')
@login_required
@admin_required
def listar_usuarios():
    """API para listar todos los usuarios"""
    try:
        usuarios = Usuario.query.all()
        usuarios_data = []
        
        for usuario in usuarios:
            usuarios_data.append({
                'id': usuario.id,
                'username': usuario.username,
                'email': usuario.email,
                'nombre_completo': usuario.nombre_completo,
                'rol': usuario.rol,
                'activo': usuario.activo,
                'fecha_creacion': usuario.fecha_creacion.isoformat() if usuario.fecha_creacion else None,
                'ultimo_acceso': usuario.ultimo_acceso.isoformat() if usuario.ultimo_acceso else None,
                'cantidad_casos': len(usuario.casos)
            })
        
        return jsonify({'success': True, 'usuarios': usuarios_data})
        
    except Exception as e:
        print(f"Error obteniendo usuarios: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/crear-usuario', methods=['POST'])
@login_required
@admin_required
def crear_usuario():
    """API para crear un nuevo usuario"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        required_fields = ['username', 'email', 'nombre_completo', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Campo requerido: {field}'}), 400
        
        # Validar longitud de contraseña
        if len(data['password']) < 6:
            return jsonify({'success': False, 'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
        
        # Verificar si el usuario ya existe
        if Usuario.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'error': 'El nombre de usuario ya existe'}), 400
        
        if Usuario.query.filter_by(email=data['email']).first():
            return jsonify({'success': False, 'error': 'El email ya está registrado'}), 400
        
        # Crear usuario
        nuevo_usuario = Usuario(
            username=data['username'],
            email=data['email'],
            nombre_completo=data['nombre_completo'],
            rol=data.get('rol', 'usuario'),
            activo=data.get('activo', True),
            assemblyai_key=data.get('assemblyai_key')
        )
        nuevo_usuario.set_password(data['password'])
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        # Log del evento
        SistemaLogging.log_user_create(current_user.username, {
            'username': data['username'],
            'email': data['email'],
            'rol': data.get('rol', 'usuario'),
            'usuario_creado_id': nuevo_usuario.id
        })
        
        return jsonify({
            'success': True,
            'mensaje': 'Usuario creado correctamente',
            'usuario_id': nuevo_usuario.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creando usuario: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/actualizar-usuario/<int:usuario_id>', methods=['PUT'])
@login_required
@admin_required
def actualizar_usuario(usuario_id):
    """API para actualizar un usuario"""
    try:
        usuario = db.session.get(Usuario, usuario_id)
        if not usuario:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
        
        data = request.get_json()
        
        # Actualizar campos
        if 'username' in data:
            # Verificar si el nuevo username ya existe
            if data['username'] != usuario.username:
                if Usuario.query.filter_by(username=data['username']).first():
                    return jsonify({'success': False, 'error': 'El nombre de usuario ya existe'}), 400
            usuario.username = data['username']
        
        if 'email' in data:
            # Verificar si el nuevo email ya existe
            if data['email'] != usuario.email:
                if Usuario.query.filter_by(email=data['email']).first():
                    return jsonify({'success': False, 'error': 'El email ya está registrado'}), 400
            usuario.email = data['email']
        
        if 'nombre_completo' in data:
            usuario.nombre_completo = data['nombre_completo']
        
        if 'rol' in data:
            usuario.rol = data['rol']
        
        if 'activo' in data:
            usuario.activo = data['activo']
        
        if 'assemblyai_key' in data:
            usuario.assemblyai_key = data['assemblyai_key']
        
        # Actualizar contraseña si se proporciona
        if data.get('password'):
            if len(data['password']) < 6:
                return jsonify({'success': False, 'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
            usuario.set_password(data['password'])
        
        db.session.commit()
        
        # Log del evento
        log_evento(
            'USUARIO_ACTUALIZADO_ADMIN',
            f'Usuario actualizado por admin: {usuario.username}',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'usuario_actualizado_id': usuario_id}
        )
        
        return jsonify({
            'success': True,
            'mensaje': 'Usuario actualizado correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error actualizando usuario: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/eliminar-usuario/<int:usuario_id>', methods=['DELETE'])
@login_required
@admin_required
def eliminar_usuario(usuario_id):
    """API para eliminar un usuario"""
    try:
        usuario = db.session.get(Usuario, usuario_id)
        if not usuario:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
        
        # No permitir eliminar el propio usuario
        if usuario.id == current_user.id:
            return jsonify({'success': False, 'error': 'No puedes eliminar tu propio usuario'}), 400
        
        # No permitir eliminar al último admin
        if usuario.rol == 'admin':
            admin_count = Usuario.query.filter_by(rol='admin', activo=True).count()
            if admin_count <= 1:
                return jsonify({'success': False, 'error': 'No se puede eliminar al último administrador'}), 400
        
        # Eliminar el usuario
        db.session.delete(usuario)
        db.session.commit()
        
        # Log del evento
        log_evento(
            'USUARIO_ELIMINADO_ADMIN',
            f'Usuario eliminado por admin: {usuario.username}',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'usuario_eliminado_id': usuario_id}
        )
        
        return jsonify({
            'success': True,
            'mensaje': 'Usuario eliminado correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error eliminando usuario: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/casos')
@login_required
@admin_required
def listar_casos_admin():
    """API para listar todos los casos (admin)"""
    try:
        casos = Caso.query.order_by(Caso.fecha_creacion.desc()).all()
        casos_data = []
        
        for caso in casos:
            casos_data.append({
                'id': caso.id,
                'sesion_id': caso.sesion_id,
                'nombre_caso': caso.nombre_caso,
                'numero_informe_tecnico': caso.numero_informe_tecnico,
                'expediente': caso.expediente,
                'origen_solicitud': caso.origen_solicitud,
                'fecha_intervencion': caso.fecha_intervencion.isoformat() if caso.fecha_intervencion else None,
                'hora_intervencion': caso.hora_intervencion.isoformat() if caso.hora_intervencion else None,
                'tipo_requerimiento': caso.tipo_requerimiento,
                'estado_caso': caso.estado_caso,
                'completado': caso.completado,
                'fecha_creacion': caso.fecha_creacion.isoformat(),
                'usuario_id': caso.usuario_id,
                'usuario_nombre': caso.usuario.nombre_completo if caso.usuario else 'N/A',
                'cantidad_archivos': len(caso.archivos)
            })
        
        return jsonify({'success': True, 'casos': casos_data})
        
    except Exception as e:
        print(f"Error obteniendo casos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/estadisticas')
@login_required
@admin_required
def estadisticas():
    """API para obtener estadísticas básicas del sistema"""
    try:
        # Estadísticas de casos (sin usuarios)
        total_casos = Caso.query.count()
        casos_activos = Caso.query.filter_by(completado=False).count()
        casos_finalizados = Caso.query.filter_by(completado=True).count()
        
        # Estadísticas de archivos
        total_archivos = ArchivoCaso.query.count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_casos': total_casos,
                'casos_activos': casos_activos,
                'casos_completados': casos_finalizados,
                'total_archivos': total_archivos
            }
        })
        
    except Exception as e:
        # Log del error pero no lo imprimimos en consola
        utils.log_evento("ERROR_ESTADISTICAS", f"Error obteniendo estadísticas: {str(e)[:100]}")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

@admin_bp.route('/api/estadisticas-avanzadas')
@login_required
@admin_required
def estadisticas_avanzadas():
    """API para obtener estadísticas avanzadas con análisis mensual por tipo de requerimiento"""
    try:
        from sqlalchemy import func, extract
        from datetime import datetime, timedelta
        
        # Obtener parámetros de fecha
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', datetime.now().month, type=int)
        
        # Calcular fechas de inicio y fin del mes
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        # Estadísticas generales del mes
        casos_mes = Caso.query.filter(
            Caso.fecha_creacion >= start_date,
            Caso.fecha_creacion <= end_date
        )
        
        total_casos_mes = casos_mes.count()
        casos_activos_mes = casos_mes.filter_by(completado=False).count()
        casos_completados_mes = casos_mes.filter_by(completado=True).count()
        
        # Análisis por tipo de requerimiento - usando método simplificado
        tipos_requerimiento_query = casos_mes.with_entities(
            Caso.tipo_requerimiento,
            func.count(Caso.id).label('cantidad')
        ).group_by(Caso.tipo_requerimiento).all()
        
        # Calcular completados por separado para cada tipo
        tipos_requerimiento = []
        for tipo, cantidad in tipos_requerimiento_query:
            completados = casos_mes.filter_by(tipo_requerimiento=tipo, completado=True).count()
            tipos_requerimiento.append((tipo, cantidad, completados))
        
        # Análisis por origen de solicitud - usando método simplificado
        origenes_solicitud_query = casos_mes.with_entities(
            Caso.origen_solicitud,
            func.count(Caso.id).label('cantidad')
        ).group_by(Caso.origen_solicitud).all()
        
        # Calcular completados por separado para cada origen
        origenes_solicitud = []
        for origen, cantidad in origenes_solicitud_query:
            completados = casos_mes.filter_by(origen_solicitud=origen, completado=True).count()
            origenes_solicitud.append((origen, cantidad, completados))
        
        # Estadísticas históricas (últimos 12 meses)
        historico = []
        for i in range(12):
            fecha_ref = start_date - timedelta(days=30*i)
            mes_ref = fecha_ref.month
            año_ref = fecha_ref.year
            
            casos_historico = Caso.query.filter(
                extract('year', Caso.fecha_creacion) == año_ref,
                extract('month', Caso.fecha_creacion) == mes_ref
            )
            
            historico.append({
                'mes': mes_ref,
                'año': año_ref,
                'total': casos_historico.count(),
                'completados': casos_historico.filter_by(completado=True).count(),
                'activos': casos_historico.filter_by(completado=False).count()
            })
        
        # Preparar datos de tipos de requerimiento
        tipos_data = []
        for tipo, cantidad, completados in tipos_requerimiento:
            tipos_data.append({
                'tipo': tipo or 'Sin especificar',
                'total': cantidad,
                'completados': completados,
                'activos': cantidad - completados,
                'porcentaje_completado': round((completados / cantidad * 100) if cantidad > 0 else 0, 1)
            })
        
        # Preparar datos de orígenes
        origenes_data = []
        for origen, cantidad, completados in origenes_solicitud:
            origenes_data.append({
                'origen': origen or 'Sin especificar',
                'total': cantidad,
                'completados': completados,
                'activos': cantidad - completados,
                'porcentaje_completado': round((completados / cantidad * 100) if cantidad > 0 else 0, 1)
            })
        
        return jsonify({
            'success': True,
            'periodo': {
                'año': year,
                'mes': month,
                'nombre_mes': start_date.strftime('%B'),
                'fecha_inicio': start_date.isoformat(),
                'fecha_fin': end_date.isoformat()
            },
            'estadisticas_mes': {
                'total_casos': total_casos_mes,
                'casos_activos': casos_activos_mes,
                'casos_completados': casos_completados_mes,
                'porcentaje_completado': round((casos_completados_mes / total_casos_mes * 100) if total_casos_mes > 0 else 0, 1)
            },
            'por_tipo_requerimiento': tipos_data,
            'por_origen_solicitud': origenes_data,
            'historico': list(reversed(historico))  # Más reciente primero
        })
        
    except Exception as e:
        utils.log_evento("ERROR_ESTADISTICAS_AVANZADAS", f"Error obteniendo estadísticas avanzadas: {str(e)[:100]}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/debug-casos')
@login_required
def debug_casos():
    """API de debug para verificar casos en la base de datos"""
    try:
        from models import Caso
        from sqlalchemy import text
        
        # Contar total de casos
        total_casos = Caso.query.count()
        
        # Obtener los últimos 5 casos
        ultimos_casos = Caso.query.order_by(Caso.fecha_creacion.desc()).limit(5).all()
        
        casos_info = []
        for caso in ultimos_casos:
            casos_info.append({
                'id': caso.id,
                'sesion_id': caso.sesion_id,
                'expediente': caso.expediente,
                'numero_informe_tecnico': caso.numero_informe_tecnico,
                'usuario_id': caso.usuario_id,
                'fecha_creacion': caso.fecha_creacion.isoformat(),
                'completado': caso.completado
            })
        
        return jsonify({
            'success': True,
            'total_casos': total_casos,
            'ultimos_casos': casos_info
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/estadisticas/exportar')
@login_required
@admin_required
def exportar_estadisticas():
    """API para exportar estadísticas en CSV"""
    try:
        import csv
        import io
        from flask import Response
        from datetime import datetime
        
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', datetime.now().month, type=int)
        
        # Obtener datos de estadísticas avanzadas
        from sqlalchemy import func, extract
        from datetime import timedelta
        
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        casos_mes = Caso.query.filter(
            Caso.fecha_creacion >= start_date,
            Caso.fecha_creacion <= end_date
        )
        
        # Datos por tipo de requerimiento - usando método simplificado
        tipos_requerimiento_query = casos_mes.with_entities(
            Caso.tipo_requerimiento,
            func.count(Caso.id).label('cantidad')
        ).group_by(Caso.tipo_requerimiento).all()
        
        # Calcular completados por separado para cada tipo
        tipos_requerimiento = []
        for tipo, cantidad in tipos_requerimiento_query:
            completados = casos_mes.filter_by(tipo_requerimiento=tipo, completado=True).count()
            tipos_requerimiento.append((tipo, cantidad, completados))
        
        # Crear CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Encabezados
        writer.writerow(['ESTADÍSTICAS MENSUALES - ' + start_date.strftime('%B %Y').upper()])
        writer.writerow([])
        writer.writerow(['TIPO DE REQUERIMIENTO', 'TOTAL CASOS', 'COMPLETADOS', 'ACTIVOS', '% COMPLETADO'])
        
        # Datos
        for tipo, cantidad, completados in tipos_requerimiento:
            activos = cantidad - completados
            porcentaje = round((completados / cantidad * 100) if cantidad > 0 else 0, 1)
            writer.writerow([
                tipo or 'Sin especificar',
                cantidad,
                completados,
                activos,
                f"{porcentaje}%"
            ])
        
        # Preparar respuesta
        output.seek(0)
        filename = f"estadisticas_{year}_{month:02d}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        print(f"Error exportando estadísticas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== SISTEMA DE LOGS ====================

@admin_bp.route('/api/logs')
@login_required
@admin_required
def obtener_logs():
    """API para obtener logs del sistema con filtros avanzados"""
    try:
        # Parámetros de filtrado
        categoria = request.args.get('categoria', '')
        tipo_evento = request.args.get('tipo_evento', '')
        usuario_id = request.args.get('usuario_id', type=int)
        fecha_desde = request.args.get('fecha_desde', '')
        fecha_hasta = request.args.get('fecha_hasta', '')
        busqueda = request.args.get('busqueda', '')
        pagina = request.args.get('pagina', 1, type=int)
        por_pagina = request.args.get('por_pagina', 50, type=int)
        
        # Construir consulta base
        query = LogEvento.query
        
        # Aplicar filtros
        if categoria:
            query = query.filter(LogEvento.tipo_evento.like(f'%{categoria}%'))
        
        if tipo_evento:
            query = query.filter(LogEvento.tipo_evento == tipo_evento)
        
        if usuario_id:
            query = query.filter(LogEvento.usuario_id == usuario_id)
        
        if fecha_desde:
            try:
                fecha_desde_obj = datetime.datetime.strptime(fecha_desde, '%Y-%m-%d')
                query = query.filter(LogEvento.fecha_evento >= fecha_desde_obj)
            except ValueError:
                pass
        
        if fecha_hasta:
            try:
                fecha_hasta_obj = datetime.datetime.strptime(fecha_hasta, '%Y-%m-%d')
                # Agregar 23:59:59 para incluir todo el día
                fecha_hasta_obj = fecha_hasta_obj.replace(hour=23, minute=59, second=59)
                query = query.filter(LogEvento.fecha_evento <= fecha_hasta_obj)
            except ValueError:
                pass
        
        if busqueda:
            query = query.filter(
                LogEvento.descripcion.like(f'%{busqueda}%') |
                LogEvento.tipo_evento.like(f'%{busqueda}%')
            )
        
        # Ordenar por fecha más reciente
        query = query.order_by(LogEvento.fecha_evento.desc())
        
        # Paginación
        logs_paginados = query.paginate(
            page=pagina, 
            per_page=por_pagina, 
            error_out=False
        )
        
        # Preparar datos de respuesta
        logs_data = []
        for log in logs_paginados.items:
            logs_data.append({
                'id': log.id,
                'tipo_evento': log.tipo_evento,
                'descripcion': log.descripcion,
                'usuario': {
                    'id': log.usuario.id if log.usuario else None,
                    'username': log.usuario.username if log.usuario else 'Sistema',
                    'nombre_completo': log.usuario.nombre_completo if log.usuario else 'Sistema'
                } if log.usuario else None,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'fecha_evento': log.fecha_evento.isoformat(),
                'datos_adicionales': log.datos_adicionales or {}
            })
        
        return jsonify({
            'success': True,
            'logs': logs_data,
            'paginacion': {
                'pagina_actual': logs_paginados.page,
                'total_paginas': logs_paginados.pages,
                'total_registros': logs_paginados.total,
                'por_pagina': por_pagina,
                'tiene_anterior': logs_paginados.has_prev,
                'tiene_siguiente': logs_paginados.has_next
            },
            'filtros_disponibles': {
                'categorias': list(SistemaLogging.CATEGORIAS.keys()),
                'eventos': list(SistemaLogging.EVENTOS.keys()),
                'usuarios': [{'id': u.id, 'username': u.username} for u in Usuario.query.all()]
            }
        })
        
    except Exception as e:
        print(f"Error obteniendo logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/logs/estadisticas')
@login_required
@admin_required
def estadisticas_logs():
    """API para obtener estadísticas de los logs"""
    try:
        from sqlalchemy import func, extract
        
        # Estadísticas generales
        total_logs = LogEvento.query.count()
        
        # Logs por categoría (últimos 30 días)
        fecha_limite = datetime.datetime.now() - datetime.timedelta(days=30)
        logs_recientes = LogEvento.query.filter(LogEvento.fecha_evento >= fecha_limite)
        
        # Top 5 tipos de eventos más frecuentes
        top_eventos = db.session.query(
            LogEvento.tipo_evento,
            func.count(LogEvento.id).label('cantidad')
        ).filter(
            LogEvento.fecha_evento >= fecha_limite
        ).group_by(
            LogEvento.tipo_evento
        ).order_by(
            func.count(LogEvento.id).desc()
        ).limit(5).all()
        
        # Logs por día (últimos 7 días)
        logs_por_dia = []
        for i in range(7):
            fecha = datetime.datetime.now() - datetime.timedelta(days=i)
            inicio_dia = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
            fin_dia = fecha.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            cantidad = LogEvento.query.filter(
                LogEvento.fecha_evento >= inicio_dia,
                LogEvento.fecha_evento <= fin_dia
            ).count()
            
            logs_por_dia.append({
                'fecha': fecha.strftime('%Y-%m-%d'),
                'cantidad': cantidad
            })
        
        # Usuarios más activos (últimos 30 días)
        usuarios_activos = db.session.query(
            Usuario.username,
            func.count(LogEvento.id).label('cantidad_logs')
        ).join(
            LogEvento, Usuario.id == LogEvento.usuario_id
        ).filter(
            LogEvento.fecha_evento >= fecha_limite
        ).group_by(
            Usuario.username
        ).order_by(
            func.count(LogEvento.id).desc()
        ).limit(10).all()
        
        return jsonify({
            'success': True,
            'estadisticas': {
                'total_logs': total_logs,
                'logs_ultimos_30_dias': logs_recientes.count(),
                'top_eventos': [{'tipo': e[0], 'cantidad': e[1]} for e in top_eventos],
                'logs_por_dia': logs_por_dia,
                'usuarios_activos': [{'username': u[0], 'cantidad': u[1]} for u in usuarios_activos]
            }
        })
        
    except Exception as e:
        utils.log_evento("ERROR_ESTADISTICAS_LOGS", f"Error obteniendo estadísticas de logs: {str(e)[:100]}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/logs/exportar')
@login_required
@admin_required
def exportar_logs():
    """API para exportar logs a CSV"""
    try:
        import csv
        import io
        import json
        
        # Parámetros de filtrado (mismos que obtener_logs)
        categoria = request.args.get('categoria', '')
        tipo_evento = request.args.get('tipo_evento', '')
        usuario_id = request.args.get('usuario_id', type=int)
        fecha_desde = request.args.get('fecha_desde', '')
        fecha_hasta = request.args.get('fecha_hasta', '')
        busqueda = request.args.get('busqueda', '')
        
        # Construir consulta (misma lógica que obtener_logs)
        query = LogEvento.query
        
        if categoria:
            query = query.filter(LogEvento.tipo_evento.like(f'%{categoria}%'))
        if tipo_evento:
            query = query.filter(LogEvento.tipo_evento == tipo_evento)
        if usuario_id:
            query = query.filter(LogEvento.usuario_id == usuario_id)
        if fecha_desde:
            try:
                fecha_desde_obj = datetime.datetime.strptime(fecha_desde, '%Y-%m-%d')
                query = query.filter(LogEvento.fecha_evento >= fecha_desde_obj)
            except ValueError:
                pass
        if fecha_hasta:
            try:
                fecha_hasta_obj = datetime.datetime.strptime(fecha_hasta, '%Y-%m-%d')
                fecha_hasta_obj = fecha_hasta_obj.replace(hour=23, minute=59, second=59)
                query = query.filter(LogEvento.fecha_evento <= fecha_hasta_obj)
            except ValueError:
                pass
        if busqueda:
            query = query.filter(
                LogEvento.descripcion.like(f'%{busqueda}%') |
                LogEvento.tipo_evento.like(f'%{busqueda}%')
            )
        
        # Obtener todos los logs (sin paginación para exportar)
        logs = query.order_by(LogEvento.fecha_evento.desc()).all()
        
        # Crear CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Encabezados
        writer.writerow([
            'ID', 'Fecha', 'Tipo Evento', 'Descripción', 'Usuario', 
            'IP Address', 'User Agent', 'Datos Adicionales'
        ])
        
        # Datos
        for log in logs:
            usuario_info = f"{log.usuario.username} ({log.usuario.nombre_completo})" if log.usuario else "Sistema"
            datos_adicionales = json.dumps(log.datos_adicionales, ensure_ascii=False) if log.datos_adicionales else ""
            
            writer.writerow([
                log.id,
                log.fecha_evento.strftime('%Y-%m-%d %H:%M:%S'),
                log.tipo_evento,
                log.descripcion,
                usuario_info,
                log.ip_address or '',
                log.user_agent or '',
                datos_adicionales
            ])
        
        # Preparar respuesta
        output.seek(0)
        filename = f"logs_sistema_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        response = jsonify({
            'success': True,
            'filename': filename,
            'content': output.getvalue(),
            'total_registros': len(logs)
        })
        
        return response
        
    except Exception as e:
        print(f"Error exportando logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/delete-case/<int:case_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_case(case_id):
    """Eliminar un caso (solo para admins)"""
    try:
        # Buscar el caso
        caso = db.session.get(Caso, case_id)
        if not caso:
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        # Obtener información del caso antes de eliminar
        expediente = caso.expediente
        sesion_id = caso.sesion_id
        
        # Eliminar archivos físicos del caso
        import os
        import shutil
        from config import Config
        
        carpeta_caso = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id)
        if os.path.exists(carpeta_caso):
            try:
                shutil.rmtree(carpeta_caso)
                print(f"Carpeta del caso eliminada: {carpeta_caso}")
            except Exception as e:
                print(f"Error eliminando carpeta del caso: {e}")
        
        # Eliminar el caso de la base de datos
        db.session.delete(caso)
        db.session.commit()
        
        # Log del evento
        log_evento(
            'CASO_ELIMINADO_ADMIN',
            f'Caso eliminado por admin: {expediente}',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'caso_eliminado_id': case_id, 'expediente': expediente}
        )
        
        return jsonify({
            'success': True,
            'mensaje': 'Caso eliminado exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error eliminando caso: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/backup', methods=['POST'])
@login_required
@admin_required
def admin_create_backup():
    """Crear backup de la base de datos PostgreSQL (solo para admins)"""
    try:
        import subprocess
        
        # Crear nombre de archivo con timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.sql"
        backup_path = os.path.join(os.getcwd(), backup_filename)
        
        # Crear backup de PostgreSQL usando pg_dump
        db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
        # Extraer información de conexión de la URI
        # Formato: postgresql://user:password@host:port/database
        if db_uri.startswith('postgresql://'):
            # Parsear la URI
            uri_parts = db_uri.replace('postgresql://', '').split('@')
            if len(uri_parts) == 2:
                user_pass = uri_parts[0].split(':')
                host_db = uri_parts[1].split('/')
                if len(user_pass) == 2 and len(host_db) == 2:
                    username = user_pass[0]
                    password = user_pass[1]
                    host_port = host_db[0].split(':')
                    host = host_port[0]
                    port = host_port[1] if len(host_port) > 1 else '5432'
                    database = host_db[1]
                    
                    # Configurar variable de entorno para la contraseña
                    env = os.environ.copy()
                    env['PGPASSWORD'] = password
                    
                    # Ejecutar pg_dump
                    cmd = [
                        'pg_dump',
                        '-h', host,
                        '-p', port,
                        '-U', username,
                        '-d', database,
                        '-f', backup_path
                    ]
                    
                    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                    if result.returncode != 0:
                        raise Exception(f"Error en pg_dump: {result.stderr}")
                else:
                    raise Exception("Formato de URI de base de datos inválido")
            else:
                raise Exception("Formato de URI de base de datos inválido")
        else:
            raise Exception("No es una URI de PostgreSQL válida")
        
        # Log del evento
        log_evento(
            'BACKUP_CREADO',
            f'Backup creado: {backup_filename}',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'backup_filename': backup_filename}
        )
        
        return jsonify({'success': True, 'filename': backup_filename})
    except Exception as e:
        print(f"Error creando backup: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/clear-old-data', methods=['POST'])
@login_required
@admin_required
def admin_clear_old_data():
    """Limpiar datos antiguos (solo para admins)"""
    try:
        # Limpiar casos completados de más de 30 días
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        old_casos = Caso.query.filter(
            Caso.completado == True,
            Caso.fecha_creacion < thirty_days_ago
        ).all()
        
        deleted_count = 0
        for caso in old_casos:
            # Eliminar archivos físicos del caso
            import shutil
            from config import Config
            
            carpeta_caso = os.path.join(Config.BASE_UPLOAD_FOLDER, caso.sesion_id)
            if os.path.exists(carpeta_caso):
                try:
                    shutil.rmtree(carpeta_caso)
                except Exception as e:
                    print(f"Error eliminando carpeta del caso: {e}")
            
            db.session.delete(caso)
            deleted_count += 1
        
        db.session.commit()
        
        # Log del evento
        log_evento(
            'DATOS_ANTIGUOS_LIMPIADOS',
            f'Se eliminaron {deleted_count} casos antiguos',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'casos_eliminados': deleted_count}
        )
        
        return jsonify({'success': True, 'message': f'{deleted_count} casos antiguos eliminados'})
    except Exception as e:
        db.session.rollback()
        print(f"Error limpiando datos antiguos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/clear-logs', methods=['POST'])
@login_required
@admin_required
def admin_clear_logs():
    """Limpiar logs del sistema (solo para admins)"""
    try:
        # Limpiar logs de más de 90 días
        ninety_days_ago = datetime.datetime.now() - datetime.timedelta(days=90)
        old_logs = LogEvento.query.filter(
            LogEvento.fecha_evento < ninety_days_ago
        ).all()
        
        deleted_count = 0
        for log in old_logs:
            db.session.delete(log)
            deleted_count += 1
        
        db.session.commit()
        
        # Log del evento
        log_evento(
            'LOGS_LIMPIADOS',
            f'Se eliminaron {deleted_count} logs antiguos',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'logs_eliminados': deleted_count}
        )
        
        return jsonify({'success': True, 'message': f'{deleted_count} logs antiguos eliminados'})
    except Exception as e:
        db.session.rollback()
        print(f"Error limpiando logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/update-case/<int:case_id>', methods=['PUT'])
@login_required
@admin_required
def admin_update_case(case_id):
    """Actualizar un caso (solo para admins)"""
    try:
        caso = db.session.get(Caso, case_id)
        if not caso:
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        data = request.get_json()
        
        # Actualizar campos permitidos
        if 'estado_caso' in data:
            caso.estado_caso = data['estado_caso']
        
        if 'completado' in data:
            caso.completado = data['completado']
        
        if 'observaciones' in data:
            caso.observaciones = data['observaciones']
        
        if 'datos_formulario' in data:
            caso.datos_formulario = data['datos_formulario']
        
        db.session.commit()
        
        # Log del evento
        log_evento(
            'CASO_ACTUALIZADO_ADMIN',
            f'Caso actualizado por admin: {caso.expediente}',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'caso_actualizado_id': case_id}
        )
        
        return jsonify({
            'success': True,
            'mensaje': 'Caso actualizado correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error actualizando caso: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def admin_toggle_user_status(user_id):
    """Cambiar estado de usuario (solo para admins)"""
    try:
        usuario = db.session.get(Usuario, user_id)
        if not usuario:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
        
        # No permitir desactivar al último admin
        if usuario.rol == 'admin' and usuario.activo:
            admin_count = Usuario.query.filter_by(rol='admin', activo=True).count()
            if admin_count <= 1:
                return jsonify({'success': False, 'error': 'No se puede desactivar al último administrador'}), 400
        
        # Cambiar estado
        usuario.activo = not usuario.activo
        db.session.commit()
        
        # Log del evento
        log_evento(
            'USUARIO_ESTADO_CAMBIADO',
            f'Estado de usuario cambiado: {usuario.username} - {"Activo" if usuario.activo else "Inactivo"}',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'usuario_id': user_id, 'nuevo_estado': usuario.activo}
        )
        
        return jsonify({
            'success': True,
            'mensaje': f'Usuario {"activado" if usuario.activo else "desactivado"} correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error cambiando estado de usuario: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
