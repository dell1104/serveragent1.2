# blueprints/casos.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from flask_login import login_required, current_user
from models import db, Caso, ArchivoCaso, Usuario
import utils
from config import Config
from werkzeug.utils import secure_filename
import os
import json
import datetime

casos_bp = Blueprint('casos', __name__)

@casos_bp.route('/gestion-casos')
@login_required
def gestion_casos():
    """Página de gestión de casos"""
    return render_template('gestion-casos.html')

@casos_bp.route('/api/crear-caso', methods=['POST'])
@login_required
def crear_caso():
    """API para crear un nuevo caso"""
    try:
        data = request.get_json()
        print(f"🔍 Datos recibidos en crear_caso: {data}")  # Debug log
        
        # --- INICIO DE LA SOLUCIÓN ---
        # 1. Construir el número de expediente a partir de las partes recibidas
        if data.get('expediente_prefijo') == 'Otro':
            # Si el prefijo es 'Otro', usar el campo 'expediente_otro'
            expediente_completo = data.get('expediente_otro', '').strip()
        else:
            # Si no, construirlo con prefijo, número y año
            prefijo = data.get('expediente_prefijo', '')
            numero = data.get('expediente_numero', '')
            anio = data.get('expediente_anio', '')
            expediente_completo = f"{prefijo}{numero}{anio}".strip()
        
        # 2. Añadir el expediente completo al diccionario de datos
        data['expediente'] = expediente_completo
        print(f"🏷️ Expediente construido: {expediente_completo}")  # Debug log
        # --- FIN DE LA SOLUCIÓN ---
        
        # Validar expediente con función de seguridad
        es_valido_exp, mensaje_exp = utils.validar_expediente(expediente_completo)
        if not es_valido_exp:
            utils.log_seguridad('INVALID_EXPEDIENTE', f'Expediente inválido: {expediente_completo}', 
                         request.remote_addr, request.headers.get('User-Agent'))
            return jsonify({'success': False, 'error': mensaje_exp}), 400
        
        # Sanitizar inputs del usuario
        data['origen_solicitud'] = utils.sanitizar_input_usuario(data.get('origen_solicitud', ''), 200)
        data['tipo_requerimiento'] = utils.sanitizar_input_usuario(data.get('tipo_requerimiento', ''), 100)
        data['observaciones'] = utils.sanitizar_input_usuario(data.get('observaciones', ''), 1000)
        
        # Validar datos requeridos (solo los esenciales como en el backup)
        required_fields = ['expediente', 'origen_solicitud', 'tipo_requerimiento']
        for field in required_fields:
            if not data.get(field):
                print(f"❌ Campo faltante: {field}")  # Debug log
                return jsonify({'success': False, 'error': f'Campo requerido: {field}'}), 400
        
        # Generar número de informe técnico si no se proporciona (como en el backup)
        if not data.get('numero_informe_tecnico'):
            # Generar número de informe técnico automáticamente
            año_actual = datetime.datetime.now().year
            año_corto = str(año_actual)[-2:]  # Obtener los últimos 2 dígitos del año (25 para 2025)

            # Contar casos existentes en el año actual
            casos_año_actual = Caso.query.filter(
                Caso.numero_informe_tecnico.like(f'IT%-{año_corto}')
            ).count()

            # Generar siguiente número
            siguiente_numero = casos_año_actual + 1
            data['numero_informe_tecnico'] = f"IT {siguiente_numero:02d}-{año_corto}"

        # Verificar si el número de informe ya existe
        if Caso.query.filter_by(numero_informe_tecnico=data['numero_informe_tecnico']).first():
            return jsonify({'success': False, 'error': 'El número de informe técnico ya existe'}), 400

        # Crear estructura de carpetas usando el formato correcto del respaldo
        # Formato real observado: IT 01-25_P-88888-25_Oficial-Fiscal-San-Carlos-Tunuyan
        
        # Limpiar expediente: P-88888/25 -> P-88888-25
        expediente_limpio = secure_filename(data['expediente']).replace('/', '-').replace('_', '-')
        
        # Limpiar origen: espacios y caracteres especiales -> guiones
        oficina_limpia = secure_filename(data['origen_solicitud'])
        oficina_limpia = oficina_limpia.replace(' ', '-').replace('_', '-')
        
        # Extraer solo el número del informe técnico (sin el prefijo "IT ")
        numero_sin_prefijo = data['numero_informe_tecnico']
        while numero_sin_prefijo.startswith('IT '):
            numero_sin_prefijo = numero_sin_prefijo[3:]  # Remover "IT " del inicio
            
        # Construir sesion_id exactamente como aparece en las carpetas existentes
        sesion_id = f"IT {numero_sin_prefijo}_{expediente_limpio}_{oficina_limpia}"
        
        print(f"🏷️ Sesion ID construida: {sesion_id}")  # Debug log

        # --- AÑADE ESTE PRINT PARA DEPURAR ---
        print(f"--- CREANDO CASO ---")
        print(f"Usuario actual: {current_user.username}, ID: {current_user.id}")
        # -------------------------------------
        
        # Crear el caso con el sesion_id correcto desde el principio
        nuevo_caso = Caso(
            sesion_id=sesion_id,
            nombre_caso=data.get('descripcion', f"Caso {data['numero_informe_tecnico']}"),
            expediente=data['expediente'],
            numero_informe_tecnico=data['numero_informe_tecnico'],
            fecha_intervencion=datetime.datetime.fromisoformat(data['fecha_intervencion']).date() if data.get('fecha_intervencion') else None,
            hora_intervencion=datetime.datetime.strptime(data['hora_intervencion'], '%H:%M').time() if data.get('hora_intervencion') else None,
            origen_solicitud=data['origen_solicitud'],
            tipo_requerimiento=data['tipo_requerimiento'],
            observaciones=data.get('descripcion', ''),
            usuario_id=current_user.id
        )
        
        db.session.add(nuevo_caso)
        db.session.flush()  # Para obtener el ID
        
        print(f"Caso creado con ID: {nuevo_caso.id} y User ID: {nuevo_caso.usuario_id}")
        print(f"----------------------")

        carpeta_caso = utils.crear_estructura_caso(sesion_id, nuevo_caso.expediente, nuevo_caso.origen_solicitud)

        if not carpeta_caso:
            print("❌ Error creando estructura de carpetas, haciendo rollback")
            db.session.rollback()
            return jsonify({'success': False, 'error': 'Error creando estructura de carpetas'}), 500

        print("💾 Haciendo commit a la base de datos...")
        db.session.commit()
        print("✅ Caso guardado exitosamente en la base de datos")
        
        # Log del evento
        utils.log_evento(
            'CASO_CREADO',
            f'Nuevo caso creado: {nuevo_caso.numero_informe_tecnico}',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'caso_id': nuevo_caso.id, 'expediente': nuevo_caso.expediente}
        )
        
        return jsonify({
            'success': True,
            'mensaje': 'Caso creado correctamente',
            'caso_id': nuevo_caso.id,
            'sesion_id': sesion_id,
            'numero_informe_tecnico': nuevo_caso.numero_informe_tecnico,
            'expediente': nuevo_caso.expediente,
            'origen_solicitud': nuevo_caso.origen_solicitud
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creando caso: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@casos_bp.route('/api/cargar-casos', methods=['GET'])
@login_required
def cargar_casos():
    """API para cargar todos los casos del usuario"""
    try:
        casos = Caso.query.filter_by(usuario_id=current_user.id).order_by(Caso.fecha_creacion.desc()).all()
        
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
                'cantidad_archivos': len(caso.archivos)
            })
        
        return jsonify({'success': True, 'casos': casos_data})
        
    except Exception as e:
        print(f"Error cargando casos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@casos_bp.route('/api/subir-archivo-caso', methods=['POST'])
@login_required
def subir_archivo_caso():
    """API para subir archivo a un caso específico con validaciones de seguridad mejoradas"""
    try:
        # Validar que se envió un archivo
        if 'archivo' not in request.files:
            utils.log_seguridad('FILE_UPLOAD_ATTEMPT', 'Intento de subida sin archivo', 
                         request.remote_addr, request.headers.get('User-Agent'))
            return jsonify({'success': False, 'error': 'No se seleccionó ningún archivo'}), 400
        
        archivo = request.files['archivo']
        sesion_id = request.form.get('sesion_id')
        
        if not sesion_id:
            utils.log_seguridad('FILE_UPLOAD_ATTEMPT', 'Intento de subida sin sesion_id', 
                         request.remote_addr, request.headers.get('User-Agent'))
            return jsonify({'success': False, 'error': 'ID de sesión requerido'}), 400
        
        # Validar archivo con las nuevas funciones de seguridad
        es_valido, mensaje_error, tipo_mime = utils.validar_archivo_seguro(archivo, max_size_mb=100)
        if not es_valido:
            utils.log_seguridad('FILE_UPLOAD_REJECTED', f'Archivo rechazado: {mensaje_error}', 
                         request.remote_addr, request.headers.get('User-Agent'))
            return jsonify({'success': False, 'error': mensaje_error}), 400
        
        # Buscar el caso por sesion_id
        caso = Caso.query.filter_by(sesion_id=sesion_id).first()
        if not caso or caso.usuario_id != current_user.id:
            utils.log_seguridad('FILE_UPLOAD_UNAUTHORIZED', f'Intento de subida a caso no autorizado: {sesion_id}', 
                         request.remote_addr, request.headers.get('User-Agent'))
            return jsonify({'success': False, 'error': 'Caso no encontrado o sin permisos'}), 404
        
        # Crear nombre de archivo seguro (ya validado)
        nombre_original = archivo.filename
        extension = os.path.splitext(nombre_original)[1].lower().lstrip('.')
        tipo_archivo = utils.clasificar_tipo_archivo(extension)
        
        nombre_archivo = utils.generar_nombre_archivo_seguro(nombre_original)
        
        # Determinar carpeta de destino según el tipo
        if tipo_archivo == 'audio':
            carpeta_destino = 'archivos_aportados'
        elif tipo_archivo == 'video':
            carpeta_destino = 'archivos_aportados'
        elif tipo_archivo == 'image':
            carpeta_destino = 'archivos_aportados'
        elif tipo_archivo == 'document':
            carpeta_destino = 'archivos_aportados'
        else:
            carpeta_destino = 'archivos_aportados'
        
        # Crear ruta de destino usando la sesion_id del caso
        ruta_destino = os.path.join(Config.BASE_UPLOAD_FOLDER, caso.sesion_id, carpeta_destino)
        os.makedirs(ruta_destino, exist_ok=True)
        
        ruta_archivo = os.path.join(ruta_destino, nombre_archivo)
        archivo.save(ruta_archivo)
        
        # Calcular hash
        hash_sha256 = utils.calcular_hash_sha256(ruta_archivo)
        if not hash_sha256:
            os.remove(ruta_archivo)
            return jsonify({'success': False, 'error': 'Error calculando hash del archivo'}), 500
        
        # Guardar en base de datos
        nuevo_archivo = ArchivoCaso(
            nombre_original=nombre_original,
            nombre_archivo=nombre_archivo,
            ruta_archivo=ruta_archivo,
            hash_sha256=hash_sha256,
            tipo_archivo=tipo_archivo,
            tamaño_bytes=os.path.getsize(ruta_archivo),
            caso_id=caso.id
        )
        
        db.session.add(nuevo_archivo)
        db.session.commit()
        
        # Guardar hash en archivo TXT
        utils.guardar_hash_archivo(ruta_archivo, hash_sha256, os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id, 'evidencia_en_proceso'))
        
        # Log del evento
        utils.log_evento(
            'ARCHIVO_SUBIDO',
            f'Archivo subido: {nombre_original} al caso {caso.numero_informe_tecnico}',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'caso_id': caso.id, 'archivo_id': nuevo_archivo.id, 'tipo': tipo_archivo}
        )
        
        return jsonify({
            'success': True,
            'mensaje': 'Archivo subido correctamente',
            'archivo': {
                'id': nuevo_archivo.id,
                'nombre_original': nombre_original,
                'tipo': tipo_archivo,
                'hash': hash_sha256[:16] + '...'
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error subiendo archivo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@casos_bp.route('/api/estructura-caso/<sesion_id>', methods=['GET'])
@login_required
def obtener_estructura_caso(sesion_id):
    """API para obtener la estructura de carpetas de un caso"""
    try:
        # Usar sesion_id directamente (ya está sanitizado al crearse)
        carpeta_caso = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id)
        
        if not os.path.exists(carpeta_caso):
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        estructura = {
            'carpeta_principal': carpeta_caso,
            'subcarpetas': {}
        }
        
        subcarpetas = ['acta', 'informe_tecnico', 'archivos_aportados', 'evidencia_en_proceso']
        
        for subcarpeta in subcarpetas:
            ruta_subcarpeta = os.path.join(carpeta_caso, subcarpeta)
            if os.path.exists(ruta_subcarpeta):
                archivos = []
                for archivo in os.listdir(ruta_subcarpeta):
                    ruta_archivo = os.path.join(ruta_subcarpeta, archivo)
                    if os.path.isfile(ruta_archivo):
                        archivos.append({
                            'nombre': archivo,
                            'tamaño': os.path.getsize(ruta_archivo),
                            'fecha_modificacion': os.path.getmtime(ruta_archivo)
                        })
                
                estructura['subcarpetas'][subcarpeta] = {
                    'ruta': ruta_subcarpeta,
                    'archivos': archivos
                }
        
        return jsonify({'success': True, 'estructura': estructura})
        
    except Exception as e:
        print(f"Error obteniendo estructura: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@casos_bp.route('/servir-archivo-evidencia/<sesion_id>/<filename>')
@login_required
def servir_archivo_evidencia(sesion_id, filename):
    """Servir archivos de evidencia para el portal del cliente"""
    try:
        # Usar sesion_id directamente (ya está sanitizado al crearse)
        # Buscar en diferentes carpetas de evidencia
        carpetas_evidencia = ['archivos_aportados', 'evidencia_en_proceso', 'acta', 'informe_tecnico']
        
        for carpeta in carpetas_evidencia:
            ruta_archivo = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id, carpeta, filename)
            if os.path.exists(ruta_archivo):
                return send_from_directory(os.path.dirname(ruta_archivo), os.path.basename(ruta_archivo))
        
        return jsonify({'error': 'Archivo no encontrado'}), 404
        
    except Exception as e:
        print(f"Error sirviendo archivo: {e}")
        return jsonify({'error': str(e)}), 500

@casos_bp.route('/api/casos_completos')
@login_required
def casos_completos():
    """Obtener todos los casos con información completa"""
    try:
        casos = Caso.query.order_by(Caso.fecha_creacion.desc()).all()
        casos_data = []
        
        for caso in casos:
            casos_data.append({
                'id': caso.id,
                'sesion_id': caso.sesion_id,
                'nombre_caso': caso.nombre_caso,
                'expediente': caso.expediente,
                'numero_informe_tecnico': caso.numero_informe_tecnico,
                'fecha_intervencion': caso.fecha_intervencion.strftime('%Y-%m-%d') if caso.fecha_intervencion else None,
                'hora_intervencion': caso.hora_intervencion.strftime('%H:%M') if caso.hora_intervencion else None,
                'origen_solicitud': caso.origen_solicitud,
                'tipo_requerimiento': caso.tipo_requerimiento,
                'estado_caso': caso.estado_caso,
                'observaciones': caso.observaciones,
                'fecha_creacion': caso.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S'),
                'completado': caso.completado
            })
        
        return jsonify({"success": True, "casos": casos_data})
        
    except Exception as e:
        print(f"❌ Error al obtener casos completos: {e}")
        return jsonify({"error": str(e)}), 500

@casos_bp.route('/api/casos_activos')
@login_required
def casos_activos():
    """Obtener casos activos (admin ve todos, usuario ve solo los suyos)"""
    try:
        if current_user.is_admin():
            # Administradores ven todos los casos activos
            casos = Caso.query.filter_by(completado=False).order_by(Caso.fecha_creacion.desc()).all()
        else:
            # Usuarios regulares ven solo sus propios casos activos
            casos = Caso.query.filter_by(usuario_id=current_user.id, completado=False).order_by(Caso.fecha_creacion.desc()).all()
        
        return jsonify([{'sesion_id': c.sesion_id, 'nombre_caso': c.nombre_caso} for c in casos])
    except Exception as e:
        print(f"❌ Error al obtener casos activos: {e}")
        return jsonify({"error": str(e)}), 500

@casos_bp.route('/api/casos_finalizados')
@login_required
def casos_finalizados():
    """Obtener casos finalizados (admin ve todos, usuario ve solo los suyos)"""
    try:
        if current_user.is_admin():
            # Administradores ven todos los casos finalizados
            casos = Caso.query.filter_by(completado=True).order_by(Caso.fecha_creacion.desc()).all()
        else:
            # Usuarios regulares ven solo sus propios casos finalizados
            casos = Caso.query.filter_by(usuario_id=current_user.id, completado=True).order_by(Caso.fecha_creacion.desc()).all()
        
        return jsonify([{'sesion_id': c.sesion_id, 'nombre_caso': c.nombre_caso} for c in casos])
    except Exception as e:
        print(f"❌ Error al obtener casos finalizados: {e}")
        return jsonify({"error": str(e)}), 500

@casos_bp.route('/api/reabrir-caso/<sesion_id>', methods=['POST'])
@login_required
def reabrir_caso(sesion_id):
    """Reabrir un caso completado"""
    try:
        caso = Caso.query.filter_by(sesion_id=sesion_id).first()
        if not caso:
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        if caso.usuario_id != current_user.id and not current_user.es_admin:
            return jsonify({'success': False, 'error': 'No tienes permisos para este caso'}), 403
        
        caso.completado = False
        caso.estado_caso = 'En Proceso'
        db.session.commit()
        
        return jsonify({'success': True, 'mensaje': 'Caso reabierto correctamente'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error reabriendo caso: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@casos_bp.route('/api/completar-caso/<sesion_id>', methods=['POST'])
@login_required
def completar_caso(sesion_id):
    """Completar un caso"""
    try:
        caso = Caso.query.filter_by(sesion_id=sesion_id).first()
        if not caso:
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        if caso.usuario_id != current_user.id and not current_user.es_admin:
            return jsonify({'success': False, 'error': 'No tienes permisos para este caso'}), 403
        
        caso.completado = True
        caso.estado_caso = 'Completado'
        db.session.commit()
        
        return jsonify({'success': True, 'mensaje': 'Caso completado correctamente'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error completando caso: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@casos_bp.route('/api/guardar-datos-caso/<sesion_id>', methods=['POST'])
@login_required
def guardar_datos_caso(sesion_id):
    """Guardar datos adicionales del caso"""
    try:
        caso = Caso.query.filter_by(sesion_id=sesion_id).first()
        if not caso:
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        if caso.usuario_id != current_user.id and not current_user.es_admin:
            return jsonify({'success': False, 'error': 'No tienes permisos para este caso'}), 403
        
        data = request.get_json()
        caso.datos_formulario = json.dumps(data)
        db.session.commit()
        
        return jsonify({'success': True, 'mensaje': 'Datos guardados correctamente'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error guardando datos del caso: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@casos_bp.route('/api/datos-caso/<sesion_id>')
@login_required
def datos_caso(sesion_id):
    """Obtener datos del caso"""
    try:
        caso = Caso.query.filter_by(sesion_id=sesion_id).first()
        if not caso:
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        if caso.usuario_id != current_user.id and not current_user.es_admin:
            return jsonify({'success': False, 'error': 'No tienes permisos para este caso'}), 403
        
        datos = {}
        if caso.datos_formulario:
            try:
                datos = json.loads(caso.datos_formulario)
            except:
                datos = {}
        
        return jsonify({
            'success': True,
            'datos': datos,
            'caso': {
                'sesion_id': caso.sesion_id,
                'nombre_caso': caso.nombre_caso,
                'expediente': caso.expediente,
                'numero_informe_tecnico': caso.numero_informe_tecnico,
                'estado_caso': caso.estado_caso,
                'completado': caso.completado
            }
        })
        
    except Exception as e:
        print(f"Error obteniendo datos del caso: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@casos_bp.route('/api/archivos-caso/<sesion_id>')
@login_required
def archivos_caso(sesion_id):
    """Obtener archivos del caso"""
    try:
        caso = Caso.query.filter_by(sesion_id=sesion_id).first()
        if not caso:
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        if caso.usuario_id != current_user.id and not current_user.es_admin:
            return jsonify({'success': False, 'error': 'No tienes permisos para este caso'}), 403
        
        archivos = []
        for archivo in caso.archivos:
            archivos.append({
                'id': archivo.id,
                'nombre_original': archivo.nombre_original,
                'nombre_archivo': archivo.nombre_archivo,
                'tipo_archivo': archivo.tipo_archivo,
                'tamaño_bytes': archivo.tamaño_bytes,
                'fecha_subida': archivo.fecha_subida.isoformat(),
                'descripcion': archivo.descripcion
            })
        
        return jsonify({'success': True, 'archivos': archivos})
        
    except Exception as e:
        print(f"Error obteniendo archivos del caso: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@casos_bp.route('/api/crear_caso_completo', methods=['POST'])
@login_required
def crear_caso_completo():
    """Crear un caso con todos los campos del sistema de gestión"""
    try:
        data = request.json
        
        # Validar campos requeridos (sin numero_informe_tecnico ya que se genera automáticamente)
        campos_requeridos = ['expediente', 'origen_solicitud', 'fecha_intervencion', 
                           'hora_intervencion', 'tipo_requerimiento']
        
        for campo in campos_requeridos:
            if not data.get(campo):
                return jsonify({"error": f"Campo requerido faltante: {campo}"}), 400
        
        # Generar número de informe técnico automáticamente
        año_actual = datetime.datetime.now().year
        año_corto = str(año_actual)[-2:]  # Obtener los últimos 2 dígitos del año (25 para 2025)
        
        # Contar casos existentes en el año actual
        casos_año_actual = Caso.query.filter(
            Caso.numero_informe_tecnico.like(f'IT%-{año_corto}')
        ).count()
        
        # Generar siguiente número
        siguiente_numero = casos_año_actual + 1
        numero_informe_tecnico = f"IT {siguiente_numero:02d}-{año_corto}"
        
        # Obtener o crear sesion_id
        sesion_id = obtener_o_crear_sesion_id(data['expediente'], data.get('origen_solicitud'))
        
        # Crear estructura de directorios del caso (simplificada)
        sesion_path = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id)
        subcarpetas = [
            'acta',                    # Actas generadas
            'informe_tecnico',         # Informes técnicos
            'archivos_aportados',      # Archivos subidos por el portal o usuario
            'evidencia_en_proceso'     # Resultados de transcripciones y otros procesos
        ]
        
        # Crear directorio principal del caso
        os.makedirs(sesion_path, exist_ok=True)
        
        # Crear subcarpetas
        for subcarpeta in subcarpetas:
            os.makedirs(os.path.join(sesion_path, subcarpeta), exist_ok=True)
        
        # Convertir fecha y hora
        fecha_intervencion = datetime.datetime.strptime(data['fecha_intervencion'], '%Y-%m-%d').date()
        hora_intervencion = datetime.datetime.strptime(data['hora_intervencion'], '%H:%M').time()
        
        # Crear nuevo caso
        nuevo_caso = Caso(
            sesion_id=sesion_id,
            nombre_caso=f"Caso {numero_informe_tecnico}",  # Nombre automático
            expediente=data['expediente'],
            numero_informe_tecnico=numero_informe_tecnico,
            fecha_intervencion=fecha_intervencion,
            hora_intervencion=hora_intervencion,
            origen_solicitud=data['origen_solicitud'],
            tipo_requerimiento=data['tipo_requerimiento'],
            observaciones=data.get('observaciones', ''),
            estado_caso='En Proceso',
            usuario_id=current_user.id
        )
        
        db.session.add(nuevo_caso)
        db.session.commit()
        
        print(f"✅ Caso creado: {sesion_id} - {nuevo_caso.nombre_caso}")
        return jsonify({
            "success": True,
            "sesion_id": sesion_id,
            "message": "Caso creado exitosamente"
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al crear caso completo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def obtener_o_crear_sesion_id(expediente, origen_solicitud):
    """Obtener o crear sesion_id basado en expediente y origen"""
    try:
        # Limpiar expediente y origen
        expediente_limpio = secure_filename(expediente).replace('/', '-').replace('_', '-')
        oficina_limpia = secure_filename(origen_solicitud or "OFICINA_FISCAL")
        oficina_limpia = oficina_limpia.replace(' ', '-').replace('_', '-')
        
        # Generar número de informe técnico
        año_actual = datetime.datetime.now().year
        año_corto = str(año_actual)[-2:]
        
        # Contar casos existentes en el año actual
        casos_año_actual = Caso.query.filter(
            Caso.numero_informe_tecnico.like(f'IT%-{año_corto}')
        ).count()
        
        siguiente_numero = casos_año_actual + 1
        numero_informe_tecnico = f"IT {siguiente_numero:02d}-{año_corto}"
        
        # Construir sesion_id
        numero_sin_prefijo = numero_informe_tecnico.replace('IT ', '').replace('-', '')
        sesion_id = f"IT {numero_sin_prefijo}_{expediente_limpio}_{oficina_limpia}"
        
        return sesion_id
        
    except Exception as e:
        print(f"❌ Error generando sesion_id: {e}")
        # Fallback con timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        return f"IT_FALLBACK_{timestamp}"
