# blueprints/api.py
from flask import Blueprint, request, jsonify, send_from_directory
from flask_login import login_required, current_user
from models import db, Caso, ArchivoCaso, Usuario, FirmaPermanente
import utils
from config import Config
import os
import datetime
import requests
import time
import re
import json
import zipfile
import shutil
from werkzeug.utils import secure_filename

api_bp = Blueprint('api', __name__)

# =============================
#  APIs DE FIRMAS
# =============================

@api_bp.route('/get-permanent-signatures', methods=['GET'])
@login_required
def get_permanent_signatures():
    """Obtener firmas permanentes"""
    try:
        firmas = FirmaPermanente.query.all()
        signatures = {f.nombre: {'signature': f.signature_data} for f in firmas}
        return jsonify(signatures)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/save-permanent-signature', methods=['POST'])
@login_required
def save_permanent_signature():
    """Guardar firma permanente"""
    try:
        data = request.get_json()
        name = data.get('name')
        signature_data = data.get('signature')
        
        if not name or not signature_data:
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
        
        # Buscar firma existente
        firma = FirmaPermanente.query.filter_by(nombre=name).first()
        
        if firma:
            # Actualizar firma existente
            firma.signature_data = signature_data
            firma.usuario_creador = current_user.nombre_completo
        else:
            # Crear nueva firma
            firma = FirmaPermanente(
                nombre=name,
                signature_data=signature_data,
                usuario_creador=current_user.nombre_completo
            )
            db.session.add(firma)
        
        db.session.commit()
        return jsonify({'message': 'Firma guardada exitosamente.'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/delete-permanent-signature/<path:name>', methods=['DELETE'])
@login_required
def delete_permanent_signature(name):
    """Eliminar firma permanente"""
    try:
        from urllib.parse import unquote
        firma = FirmaPermanente.query.filter_by(nombre=unquote(name)).first()
        if firma:
            db.session.delete(firma)
            db.session.commit()
            return jsonify({'message': 'Firma eliminada.'}), 200
        return jsonify({'message': 'Firma no encontrada.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================
#  APIs DE CASOS (adicionales)
# =============================

@api_bp.route('/casos', methods=['GET'])
@login_required
def get_casos():
    """Obtener todos los casos del usuario"""
    try:
        casos = Caso.query.filter_by(usuario_id=current_user.id).all()
        casos_data = []
        
        for caso in casos:
            casos_data.append({
                'id': caso.id,
                'numero_informe_tecnico': caso.numero_informe_tecnico,
                'expediente': caso.expediente,
                'oficina_fiscal': caso.origen_solicitud,
                'fecha_intervencion': caso.fecha_intervencion.isoformat() if caso.fecha_intervencion else None,
                'tipo_analisis': caso.tipo_requerimiento,
                'estado': caso.estado_caso,
                'fecha_creacion': caso.fecha_creacion.isoformat()
            })
        
        return jsonify({'success': True, 'casos': casos_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/buscar', methods=['POST'])
@login_required
def buscar():
    """Buscar en casos y archivos"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'success': False, 'error': 'Consulta vacía'}), 400
        
        # Buscar en casos
        casos = Caso.query.filter(
            db.or_(
                Caso.numero_informe_tecnico.contains(query),
                Caso.expediente.contains(query),
                Caso.origen_solicitud.contains(query),
                Caso.observaciones.contains(query)
            )
        ).filter_by(usuario_id=current_user.id).all()
        
        resultados = []
        for caso in casos:
            resultados.append({
                'tipo': 'caso',
                'id': caso.id,
                'titulo': f"Caso {caso.numero_informe_tecnico}",
                'descripcion': f"Expediente: {caso.expediente} - {caso.origen_solicitud}",
                'fecha': caso.fecha_creacion.isoformat()
            })
        
        return jsonify({'success': True, 'resultados': resultados})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/buscar-transcripcion', methods=['POST'])
@login_required
def buscar_transcripcion():
    """Busca una transcripción existente por nombre de archivo o hash"""
    try:
        data = request.get_json()
        archivo = data.get('archivo')
        hash_archivo = data.get('hash')
        
        if not archivo and not hash_archivo:
            return jsonify({'success': False, 'error': 'Se requiere nombre de archivo o hash'})
        
        # Buscar en la base de datos por nombre de archivo o hash
        from models import Transcripcion
        query = Transcripcion.query
        
        if archivo:
            query = query.filter(Transcripcion.archivo_original == archivo)
        
        if hash_archivo:
            query = query.filter(Transcripcion.hash_archivo == hash_archivo)
        
        resultado = query.first()
        
        if resultado:
            return jsonify({
                'success': True,
                'transcripcion': resultado.transcripcion_texto,
                'archivo': resultado.archivo_original,
                'hash': resultado.hash_archivo,
                'fecha': resultado.fecha_transcripcion.isoformat() if resultado.fecha_transcripcion else None
            })
        else:
            return jsonify({
                'success': False,
                'mensaje': 'No se encontró transcripción'
            })
        
    except Exception as e:
        print(f"Error buscando transcripción: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================
#  APIs DE ARCHIVOS
# =============================

@api_bp.route('/calcular-hash-archivo', methods=['POST'])
@login_required
def calcular_hash_archivo():
    """Calcular hash de un archivo"""
    try:
        if 'archivo' not in request.files:
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        archivo = request.files['archivo']
        if archivo.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        # Guardar temporalmente
        nombre_archivo = archivo.filename
        ruta_temporal = os.path.join(Config.BASE_UPLOAD_FOLDER, 'temp', nombre_archivo)
        os.makedirs(os.path.dirname(ruta_temporal), exist_ok=True)
        archivo.save(ruta_temporal)
        
        try:
            # Calcular hash
            hash_sha256 = utils.calcular_hash_sha256(ruta_temporal)
            if not hash_sha256:
                return jsonify({'success': False, 'error': 'Error calculando hash'}), 500
            
            return jsonify({
                'success': True,
                'hash': hash_sha256,
                'archivo': nombre_archivo
            })
        finally:
            # Limpiar archivo temporal
            if os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================
#  APIs DE DEBUG
# =============================

@api_bp.route('/debug-archivo-txt/<sesion_id>', methods=['GET'])
@login_required
def debug_archivo_txt(sesion_id):
    """Debug: ver contenido de archivo TXT"""
    try:
        # Buscar archivo TXT
        ruta_evidencia = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id, 'evidencia_en_proceso')
        
        if not os.path.exists(ruta_evidencia):
            return jsonify({'success': False, 'error': 'Carpeta no encontrada'}), 404
        
        archivos_txt = [f for f in os.listdir(ruta_evidencia) if f.endswith('.txt')]
        
        if not archivos_txt:
            return jsonify({'success': False, 'error': 'No se encontraron archivos TXT'}), 404
        
        # Tomar el más reciente
        archivo_txt = max(archivos_txt, key=lambda x: os.path.getmtime(os.path.join(ruta_evidencia, x)))
        archivo_txt_path = os.path.join(ruta_evidencia, archivo_txt)
        
        # Leer contenido
        with open(archivo_txt_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        return jsonify({
            'success': True,
            'archivo': archivo_txt,
            'contenido': contenido[:2000] + '...' if len(contenido) > 2000 else contenido
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/debug-transcripciones/<sesion_id>', methods=['GET'])
@login_required
def debug_transcripciones(sesion_id):
    """Debug: ver transcripciones parseadas"""
    try:
        # Buscar archivo TXT
        ruta_evidencia = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id, 'evidencia_en_proceso')
        
        if not os.path.exists(ruta_evidencia):
            return jsonify({'success': False, 'error': 'Carpeta no encontrada'}), 404
        
        archivos_txt = [f for f in os.listdir(ruta_evidencia) if f.startswith('transcripciones_completas_') and f.endswith('.txt')]
        
        if not archivos_txt:
            return jsonify({'success': False, 'error': 'No se encontraron archivos de transcripciones'}), 404
        
        # Tomar el más reciente
        archivo_txt = max(archivos_txt, key=lambda x: os.path.getmtime(os.path.join(ruta_evidencia, x)))
        archivo_txt_path = os.path.join(ruta_evidencia, archivo_txt)
        
        # Leer y parsear
        with open(archivo_txt_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        datos_parseados = utils.parsear_transcripciones_txt(contenido)
        
        return jsonify({
            'success': True,
            'archivo': archivo_txt,
            'estadisticas': datos_parseados['estadisticas'],
            'transcripciones': len(datos_parseados['transcripciones'])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/api/get-pending-signatures', methods=['GET'])
def get_pending_signatures(): 
    """Obtener firmas pendientes"""
    try:
        # Leer firmas pendientes desde archivo JSON
        if os.path.exists('pending_signatures.json'):
            with open('pending_signatures.json', 'r', encoding='utf-8') as f:
                pending_signatures = json.load(f)
        else:
            pending_signatures = {}
        
        return jsonify(pending_signatures)
    except Exception as e:
        print(f"Error obteniendo firmas pendientes: {e}")
        return jsonify({}), 500

@api_bp.route('/api/register-for-signing', methods=['POST'])
@login_required
def register_for_signing():
    """Registrar sesión para firma"""
    try:
        data = request.json
        session_id = data.get('sessionId')
        display_name = data.get('displayName')
        expediente = data.get('expediente')
        
        if not session_id:
            return jsonify({'error': 'sessionId es requerido'}), 400
        
        # Cargar firmas pendientes existentes
        if os.path.exists('pending_signatures.json'):
            with open('pending_signatures.json', 'r', encoding='utf-8') as f:
                pending_signatures = json.load(f)
        else:
            pending_signatures = {}
        
        # Registrar la sesión para firma
        pending_signatures[session_id] = {
            'displayName': display_name,
            'timestamp': datetime.datetime.now().isoformat(),
            'expediente': expediente
        }
        
        # Guardar en archivo
        with open('pending_signatures.json', 'w', encoding='utf-8') as f:
            json.dump(pending_signatures, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Sesión registrada para firma: {session_id} - {display_name} - Expediente: {expediente}")
        return jsonify({'message': 'Registrado para firma.', 'sessionId': session_id}), 200
        
    except Exception as e:
        print(f"❌ Error al registrar sesión para firma: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/abrir_carpeta/<sesion_id>')
@login_required
def abrir_carpeta(sesion_id):
    """Abrir la carpeta del caso en el explorador de archivos"""
    try:
        # Decodificar sesion_id de la URL
        from urllib.parse import unquote
        sesion_id = unquote(sesion_id)
        
        # Buscar el caso por sesion_id
        caso = Caso.query.filter_by(sesion_id=sesion_id).first()
        if not caso:
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        # Verificar permisos
        if caso.usuario_id != current_user.id and not current_user.es_admin:
            return jsonify({'success': False, 'error': 'No tienes permisos para este caso'}), 403
        
        # Construir ruta de la carpeta del caso
        carpeta_caso = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id)
        
        if not os.path.exists(carpeta_caso):
            return jsonify({'success': False, 'error': 'Carpeta del caso no existe'}), 404
        
        # Abrir carpeta según el sistema operativo
        import subprocess
        import platform
        
        if platform.system() == 'Windows':
            # En Windows, explorer puede devolver 1 incluso cuando funciona
            result = subprocess.run(['explorer', carpeta_caso], capture_output=True, text=True)
            print(f"Resultado de explorer: código={result.returncode}, stdout={result.stdout}, stderr={result.stderr}")
            # Si la carpeta existe, consideramos que fue exitoso independientemente del código de retorno
            if os.path.exists(carpeta_caso):
                print("Carpeta abierta correctamente (Windows)")
                return jsonify({'success': True, 'message': 'Carpeta abierta correctamente'})
            else:
                return jsonify({'success': False, 'error': 'Carpeta no existe'}), 404
        elif platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', carpeta_caso], check=True)
            print("Carpeta abierta correctamente (macOS)")
            return jsonify({'success': True, 'message': 'Carpeta abierta correctamente'})
        else:  # Linux
            subprocess.run(['xdg-open', carpeta_caso], check=True)
            print("Carpeta abierta correctamente (Linux)")
            return jsonify({'success': True, 'message': 'Carpeta abierta correctamente'})
            
    except Exception as e:
        print(f"Error abriendo carpeta: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/listar_archivos/<sesion_id>')
@login_required
def listar_archivos(sesion_id):
    """Listar archivos en la carpeta del caso"""
    try:
        # Decodificar sesion_id de la URL
        from urllib.parse import unquote
        sesion_id = unquote(sesion_id)
        
        # Buscar el caso por sesion_id
        caso = Caso.query.filter_by(sesion_id=sesion_id).first()
        if not caso:
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        # Verificar permisos
        if caso.usuario_id != current_user.id and not current_user.es_admin:
            return jsonify({'success': False, 'error': 'No tienes permisos para este caso'}), 403
        
        # Construir ruta de la carpeta del caso
        carpeta_caso = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id)
        
        if not os.path.exists(carpeta_caso):
            return jsonify({'success': False, 'error': 'Carpeta del caso no existe'}), 404
        
        # Listar archivos
        archivos = []
        for root, dirs, files in os.walk(carpeta_caso):
            for file in files:
                ruta_completa = os.path.join(root, file)
                archivos.append({
                    'nombre': file,
                    'ruta': ruta_completa,
                    'tamaño': os.path.getsize(ruta_completa),
                    'fecha_modificacion': os.path.getmtime(ruta_completa)
                })
        
        return jsonify({'success': True, 'archivos': archivos})
        
    except Exception as e:
        print(f"Error listando archivos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================
#  APIs DE HASH Y ARCHIVOS
# =============================

@api_bp.route('/guardar-hash-en-ruta', methods=['POST'])
@login_required
def guardar_hash_en_ruta():
    """Guardar archivo de hash en una ruta específica del servidor"""
    try:
        data = request.get_json()
        contenido = data.get('contenido')
        nombre_archivo = data.get('nombre_archivo')
        ruta_destino = data.get('ruta_destino')
        
        if not contenido or not nombre_archivo or not ruta_destino:
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
        
        # Validar que la ruta de destino sea segura
        ruta_destino = os.path.normpath(ruta_destino)
        if not ruta_destino.startswith(Config.BASE_UPLOAD_FOLDER):
            return jsonify({'success': False, 'error': 'Ruta de destino no permitida'}), 400
        
        # Crear la carpeta de destino si no existe
        os.makedirs(ruta_destino, exist_ok=True)
        
        # Crear la ruta completa del archivo
        ruta_archivo = os.path.join(ruta_destino, nombre_archivo)
        
        # Escribir el archivo
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        print(f"✅ Archivo de hash guardado: {ruta_archivo}")
        
        return jsonify({
            'success': True, 
            'message': 'Archivo guardado exitosamente',
            'ruta_archivo': ruta_archivo
        })
        
    except Exception as e:
        print(f"❌ Error guardando archivo de hash: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/explorar-ruta', methods=['POST'])
@login_required
def explorar_ruta():
    """Explorar una ruta del servidor y obtener archivos"""
    try:
        data = request.get_json()
        ruta = data.get('ruta')
        recursivo = data.get('recursivo', False)
        
        if not ruta:
            return jsonify({'success': False, 'error': 'Ruta no especificada'}), 400
        
        # Validar que la ruta sea segura
        ruta = os.path.normpath(ruta)
        if not os.path.exists(ruta):
            return jsonify({'success': False, 'error': 'La ruta no existe'}), 404
        
        # Explorar archivos
        archivos = []
        if recursivo:
            for root, dirs, files in os.walk(ruta):
                for file in files:
                    ruta_completa = os.path.join(root, file)
                    archivos.append({
                        'nombre': file,
                        'ruta': ruta_completa,
                        'tamaño': os.path.getsize(ruta_completa),
                        'fecha_modificacion': os.path.getmtime(ruta_completa)
                    })
        else:
            for item in os.listdir(ruta):
                ruta_completa = os.path.join(ruta, item)
                if os.path.isfile(ruta_completa):
                    archivos.append({
                        'nombre': item,
                        'ruta': ruta_completa,
                        'tamaño': os.path.getsize(ruta_completa),
                        'fecha_modificacion': os.path.getmtime(ruta_completa)
                    })
        
        return jsonify({
            'success': True,
            'archivos': archivos,
            'total': len(archivos)
        })
        
    except Exception as e:
        print(f"❌ Error explorando ruta: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500