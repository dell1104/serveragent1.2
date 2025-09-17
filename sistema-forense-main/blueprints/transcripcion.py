# blueprints/transcripcion.py
from flask import Blueprint, render_template, request, jsonify, send_from_directory
from flask_login import login_required, current_user
from models import db, Caso, Transcripcion
import utils
from config import Config
import os
import datetime
import requests
import time
import re

transcripcion_bp = Blueprint('transcripcion', __name__)

@transcripcion_bp.route('/audio-comun')
@login_required
def audio_comun():
    """Página de transcripción de audio común"""
    return render_template('audio-comun.html')

@transcripcion_bp.route('/audio-whatsapp')
@login_required
def audio_whatsapp():
    """Página de transcripción de audio de WhatsApp"""
    return render_template('audio-whatsapp.html')

@transcripcion_bp.route('/transcripcion-audios')
@login_required
def transcripcion_audios():
    """Página principal de transcripción de audios"""
    return render_template('transcripcion-audios_sidebar.html')

@transcripcion_bp.route('/api/transcribir-audio', methods=['POST'])
@login_required
def transcribir_audio():
    """API para transcribir audio usando AssemblyAI"""
    try:
        if 'archivo' not in request.files:
            return jsonify({'success': False, 'error': 'No se seleccionó ningún archivo'}), 400
        
        archivo = request.files['archivo']
        sesion_id = request.form.get('sesion_id')
        
        if not sesion_id:
            return jsonify({'success': False, 'error': 'ID de sesión requerido'}), 400
        
        if archivo.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó ningún archivo'}), 400
        
        if not utils.validar_archivo_audio(archivo.filename):
            return jsonify({'success': False, 'error': 'Tipo de archivo no válido'}), 400
        
        # Buscar el caso
        caso = Caso.query.filter_by(sesion_id=sesion_id).first()
        if not caso or caso.usuario_id != current_user.id:
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        # Guardar archivo temporalmente
        nombre_archivo = archivo.filename
        ruta_temporal = os.path.join(Config.BASE_UPLOAD_FOLDER, 'temp', nombre_archivo)
        os.makedirs(os.path.dirname(ruta_temporal), exist_ok=True)
        archivo.save(ruta_temporal)
        
        try:
            # Calcular hash
            hash_sha256 = utils.calcular_hash_sha256(ruta_temporal)
            if not hash_sha256:
                return jsonify({'success': False, 'error': 'Error calculando hash'}), 500
            
            # Subir a AssemblyAI
            headers = {
                "authorization": Config.ASSEMBLYAI_API_KEY
            }
            
            with open(ruta_temporal, "rb") as f:
                response = requests.post("https://api.assemblyai.com/v2/upload", headers=headers, data=f)
            
            if response.status_code != 200:
                return jsonify({'success': False, 'error': f'Error subiendo archivo: {response.text}'}), 500
            
            audio_url = response.json()["upload_url"]
            
            # Configurar transcripción (como en v1.2)
            data = {
                "audio_url": audio_url,
                "language_code": "es",  # Especificar idioma español
                "speaker_labels": True  # Habilitar identificación de hablantes
            }
            
            response = requests.post("https://api.assemblyai.com/v2/transcript", json=data, headers=headers)
            
            if response.status_code != 200:
                return jsonify({'success': False, 'error': f'Error iniciando transcripción: {response.text}'}), 500
            
            transcript_id = response.json()['id']
            
            # Polling para obtener resultado
            polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
            
            while True:
                transcription_result = requests.get(polling_endpoint, headers=headers).json()
                
                if transcription_result['status'] == 'completed':
                    transcripcion_texto = transcription_result['text']
                    confianza = transcription_result.get('confidence', 0.0)
                    
                    # Guardar transcripción en base de datos
                    nueva_transcripcion = Transcripcion(
                        archivo_original=nombre_archivo,
                        hash_archivo=hash_sha256,
                        transcripcion_texto=transcripcion_texto,
                        confianza=confianza,
                        idioma='es',
                        modelo_usado='conversational'
                    )
                    
                    db.session.add(nueva_transcripcion)
                    db.session.commit()
                    
                    # Log del evento
                    utils.log_evento(
                        'TRANSCRIPCION_COMPLETADA',
                        f'Transcripción completada: {nombre_archivo}',
                        current_user.id,
                        request.remote_addr,
                        request.headers.get('User-Agent'),
                        {'archivo': nombre_archivo, 'confianza': confianza}
                    )
                    
                    return jsonify({
                        'success': True,
                        'transcripcion': transcripcion_texto,
                        'confianza': confianza,
                        'archivo': nombre_archivo,
                        'hash': hash_sha256
                    })
                    
                elif transcription_result['status'] == 'error':
                    return jsonify({'success': False, 'error': f'Error en transcripción: {transcription_result.get("error", "Error desconocido")}'}), 500
                
                else:
                    time.sleep(3)
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)
        
    except Exception as e:
        print(f"Error en transcripción: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@transcripcion_bp.route('/api/guardar-transcripciones-txt', methods=['POST'])
@login_required
def guardar_transcripciones_txt():
    """API para guardar transcripciones en archivo TXT consolidado"""
    try:
        data = request.get_json()
        resultados = data.get('resultados', [])
        sesion_id = data.get('sesion_id')
        
        if not resultados or not sesion_id:
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
        
        # Buscar el caso
        caso = Caso.query.filter_by(sesion_id=sesion_id).first()
        if not caso or caso.usuario_id != current_user.id:
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        # Crear ruta del archivo TXT
        ruta_evidencia = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id, 'evidencia_en_proceso')
        os.makedirs(ruta_evidencia, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_txt = os.path.join(ruta_evidencia, f"transcripciones_completas_{timestamp}.txt")
        
        # Crear contenido del archivo
        with open(archivo_txt, 'w', encoding='utf-8') as f:
            f.write("ARCHIVO DE TRANSCRIPCIONES COMPLETAS\n")
            f.write(f"EXPEDIENTE: {caso.expediente}\n")
            f.write(f"ANALISTA: {current_user.nombre_completo}\n")
            f.write(f"FECHA: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"TOTAL DE ARCHIVOS: {len(resultados)}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, resultado in enumerate(resultados, 1):
                f.write(f"TRANSCRIPCIÓN {i} DE {len(resultados)}\n")
                f.write(f"ARCHIVO: {os.path.basename(resultado['archivo'])}\n")
                f.write(f"HASH SHA256: {resultado['hash']}\n")
                f.write(f"TAG: NO_VERIFICADO\n")  # Tag simple para no verificadas
                f.write("-" * 50 + "\n")
                f.write(resultado['transcripcion'])
                f.write("\n\n" + "=" * 80 + "\n\n")
        
        return jsonify({
            'success': True,
            'mensaje': f'Transcripciones guardadas en {os.path.basename(archivo_txt)}',
            'archivo': os.path.basename(archivo_txt)
        })
        
    except Exception as e:
        print(f"Error guardando transcripciones: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@transcripcion_bp.route('/api/cargar-transcripciones-existentes/<sesion_id>', methods=['GET'])
@login_required
def cargar_transcripciones_existentes(sesion_id):
    """API para cargar transcripciones existentes de un expediente"""
    try:
        # Buscar el caso
        caso = Caso.query.filter_by(sesion_id=sesion_id).first()
        if not caso or caso.usuario_id != current_user.id:
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        # Buscar archivo TXT de transcripciones
        ruta_evidencia = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id, 'evidencia_en_proceso')
        
        if not os.path.exists(ruta_evidencia):
            return jsonify({'success': True, 'transcripciones': [], 'estadisticas': {'corregidas': 0, 'no_corregidas': 0, 'total': 0}})
        
        # Buscar archivo TXT más reciente
        archivos_txt = [f for f in os.listdir(ruta_evidencia) if f.startswith('transcripciones_completas_') and f.endswith('.txt')]
        
        if not archivos_txt:
            return jsonify({'success': True, 'transcripciones': [], 'estadisticas': {'corregidas': 0, 'no_corregidas': 0, 'total': 0}})
        
        # Tomar el más reciente
        archivo_txt = max(archivos_txt, key=lambda x: os.path.getmtime(os.path.join(ruta_evidencia, x)))
        archivo_txt_path = os.path.join(ruta_evidencia, archivo_txt)
        
        # Leer y parsear el archivo
        with open(archivo_txt_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Parsear transcripciones
        datos_parseados = utils.parsear_transcripciones_txt(contenido)
        
        # Convertir a formato esperado por el frontend
        transcripciones = []
        for archivo, hash_archivo, transcripcion in datos_parseados['transcripciones']:
            transcripciones.append({
                'archivo': archivo,
                'hash': hash_archivo,
                'transcripcion': transcripcion
            })
        
        return jsonify({
            'success': True,
            'transcripciones': transcripciones,
            'archivo_origen': archivo_txt,
            'estadisticas': datos_parseados['estadisticas']
        })
        
    except Exception as e:
        print(f"Error cargando transcripciones: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@transcripcion_bp.route('/api/insertar-en-txt', methods=['POST'])
@login_required
def insertar_en_txt():
    """API para insertar transcripción corregida en el archivo TXT"""
    try:
        data = request.get_json()
        sesion_id = data.get('sesion_id')
        archivo = data.get('archivo')
        hash_archivo = data.get('hash')
        transcripcion = data.get('transcripcion')
        
        if not all([sesion_id, archivo, hash_archivo, transcripcion]):
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
        
        # Buscar archivo TXT
        ruta_evidencia = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id, 'evidencia_en_proceso')
        archivos_txt = [f for f in os.listdir(ruta_evidencia) if f.startswith('transcripciones_completas_') and f.endswith('.txt')]
        
        if not archivos_txt:
            return jsonify({'success': False, 'error': 'No se encontró archivo de transcripciones'}), 404
        
        archivo_txt = max(archivos_txt, key=lambda x: os.path.getmtime(os.path.join(ruta_evidencia, x)))
        archivo_txt_path = os.path.join(ruta_evidencia, archivo_txt)
        
        # Leer archivo original
        with open(archivo_txt_path, 'r', encoding='utf-8') as f:
            contenido_original = f.read()
        
        # Procesar línea por línea para reemplazar
        lineas = contenido_original.split('\n')
        lineas_nuevas = []
        i = 0
        encontrado = False
        num_transcripcion = "1"
        total_transcripciones = "1"
        
        # Buscar el bloque de la transcripción específica
        while i < len(lineas):
            linea = lineas[i]
            
            # Si encontramos el inicio de una transcripción con nuestro archivo
            if (linea.startswith('TRANSCRIPCIÓN ') and 
                i + 1 < len(lineas) and 
                lineas[i + 1] == f'ARCHIVO: {os.path.basename(archivo)}' and
                i + 2 < len(lineas) and
                lineas[i + 2] == f'HASH SHA256: {hash_archivo}' and
                i + 3 < len(lineas) and
                lineas[i + 3] == 'TAG: NO_VERIFICADO'):
                
                print(f"✅ Transcripción original encontrada en línea {i+1}")
                encontrado = True
                
                # Extraer número de transcripción
                match = re.match(r'TRANSCRIPCIÓN (\d+) DE (\d+)', linea)
                if match:
                    num_transcripcion = match.group(1)
                    total_transcripciones = match.group(2)
                
                # Saltar todo el bloque hasta el siguiente separador
                while i < len(lineas) and not lineas[i].startswith('=' * 80):
                    i += 1
                # Saltar también la línea de separadores
                i += 1
                continue
            
            # Si no es el bloque que buscamos, mantener la línea
            lineas_nuevas.append(linea)
            i += 1
        
        # Crear la nueva transcripción
        nueva_transcripcion = f"TRANSCRIPCIÓN {num_transcripcion} DE {total_transcripciones}\nTAG: VERIFICADO\nARCHIVO: {os.path.basename(archivo)}\nHASH SHA256: {hash_archivo}\nFECHA CORRECCIÓN: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nUSUARIO: {current_user.nombre_completo}\n-{50}\n{transcripcion}"
        
        if encontrado:
            print(f"✅ Transcripción original eliminada, agregando nueva")
            # Agregar la nueva transcripción al final
            contenido_nuevo = '\n'.join(lineas_nuevas).rstrip() + f"\n\n{nueva_transcripcion}\n\n{'='*80}\n"
        else:
            print(f"⚠️ No se encontró la transcripción original, agregando al final")
            contenido_nuevo = contenido_original + f"\n\n{nueva_transcripcion}\n\n{'='*80}\n"
        
        # Escribir el archivo actualizado
        print(f"💾 Escribiendo archivo actualizado...")
        with open(archivo_txt_path, 'w', encoding='utf-8') as f:
            f.write(contenido_nuevo)
        
        # Log del evento
        utils.log_evento(
            'TRANSCRIPCION_CORREGIDA',
            f'Transcripción corregida: {os.path.basename(archivo)}',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'archivo': archivo, 'hash': hash_archivo}
        )
        
        return jsonify({
            'success': True,
            'mensaje': 'Transcripción actualizada correctamente'
        })
        
    except Exception as e:
        print(f"Error insertando en TXT: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@transcripcion_bp.route('/api/transcribir-lote', methods=['POST'])
@login_required
def transcribir_lote():
    """API para transcribir múltiples audios en lote"""
    try:
        if 'archivos' not in request.files:
            return jsonify({'success': False, 'error': 'No se seleccionaron archivos'}), 400
        
        archivos = request.files.getlist('archivos')
        sesion_id = request.form.get('sesion_id')
        
        if not sesion_id:
            return jsonify({'success': False, 'error': 'ID de sesión requerido'}), 400
        
        if not archivos or archivos[0].filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionaron archivos'}), 400
        
        # Buscar el caso
        caso = Caso.query.filter_by(sesion_id=sesion_id).first()
        if not caso or caso.usuario_id != current_user.id:
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        resultados = []
        
        for archivo in archivos:
            if not utils.validar_archivo_audio(archivo.filename):
                continue
            
            # Guardar archivo temporalmente
            nombre_archivo = archivo.filename
            ruta_temporal = os.path.join(Config.BASE_UPLOAD_FOLDER, 'temp', nombre_archivo)
            os.makedirs(os.path.dirname(ruta_temporal), exist_ok=True)
            archivo.save(ruta_temporal)
            
            try:
                # Calcular hash
                hash_sha256 = utils.calcular_hash_sha256(ruta_temporal)
                if not hash_sha256:
                    continue
                
                # Subir a AssemblyAI
                headers = {"authorization": Config.ASSEMBLYAI_API_KEY}
                
                with open(ruta_temporal, "rb") as f:
                    response = requests.post("https://api.assemblyai.com/v2/upload", headers=headers, data=f)
                
                if response.status_code != 200:
                    continue
                
                audio_url = response.json()["upload_url"]
                
                # Configurar transcripción (como en v1.2)
                data = {
                    "audio_url": audio_url,
                    "language_code": "es",  # Especificar idioma español
                    "speaker_labels": True  # Habilitar identificación de hablantes
                }
                
                response = requests.post("https://api.assemblyai.com/v2/transcript", json=data, headers=headers)
                
                if response.status_code != 200:
                    continue
                
                transcript_id = response.json()['id']
                
                # Polling para obtener resultado
                polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
                
                while True:
                    transcription_result = requests.get(polling_endpoint, headers=headers).json()
                    
                    if transcription_result['status'] == 'completed':
                        transcripcion_texto = transcription_result['text']
                        confianza = transcription_result.get('confidence', 0.0)
                        
                        resultados.append({
                            'archivo': nombre_archivo,
                            'hash': hash_sha256,
                            'transcripcion': transcripcion_texto,
                            'confianza': confianza
                        })
                        break
                    elif transcription_result['status'] == 'error':
                        break
                    else:
                        time.sleep(3)
            
            finally:
                # Limpiar archivo temporal
                if os.path.exists(ruta_temporal):
                    os.remove(ruta_temporal)
        
        return jsonify({
            'success': True,
            'resultados': resultados,
            'total_procesados': len(resultados)
        })
        
    except Exception as e:
        print(f"Error en transcripción de lote: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@transcripcion_bp.route('/api/parsear-chat-whatsapp', methods=['POST'])
@login_required
def parsear_chat_whatsapp():
    """API para parsear chat de WhatsApp"""
    try:
        if 'archivo' not in request.files:
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        archivo = request.files['archivo']
        if archivo.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        # Leer contenido del archivo
        contenido = archivo.read().decode('utf-8')
        
        # Parsear chat (implementación básica)
        lineas = contenido.split('\n')
        mensajes = []
        
        for linea in lineas:
            if ' - ' in linea and ':' in linea:
                # Formato típico: [fecha] - [usuario]: [mensaje]
                partes = linea.split(' - ', 1)
                if len(partes) == 2:
                    fecha = partes[0].strip('[]')
                    resto = partes[1]
                    if ': ' in resto:
                        usuario, mensaje = resto.split(': ', 1)
                        mensajes.append({
                            'fecha': fecha,
                            'usuario': usuario.strip(),
                            'mensaje': mensaje.strip()
                        })
        
        return jsonify({
            'success': True,
            'mensajes': mensajes,
            'total': len(mensajes)
        })
        
    except Exception as e:
        print(f"Error parseando chat: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@transcripcion_bp.route('/api/insertar-transcripcion-whatsapp', methods=['POST'])
@login_required
def insertar_transcripcion_whatsapp():
    """API para insertar transcripción en chat de WhatsApp"""
    try:
        data = request.get_json()
        contenido_chat = data.get('contenido_chat')
        nombre_archivo = data.get('nombre_archivo')
        transcripcion = data.get('transcripcion')
        
        if not all([contenido_chat, nombre_archivo, transcripcion]):
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
        
        # Buscar la línea con el archivo de audio
        lineas = contenido_chat.split('\n')
        nueva_linea = f"📄 Transcripción: {transcripcion}"
        
        for i, linea in enumerate(lineas):
            if nombre_archivo in linea:
                # Insertar la transcripción después de esta línea
                lineas.insert(i + 1, nueva_linea)
                break
        
        contenido_modificado = '\n'.join(lineas)
        
        return jsonify({
            'success': True,
            'contenido_modificado': contenido_modificado
        })
        
    except Exception as e:
        print(f"Error insertando transcripción: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@transcripcion_bp.route('/api/transcribir-audio-individual', methods=['POST'])
@login_required
def transcribir_audio_individual():
    """Transcribe un archivo de audio individual"""
    try:
        data = request.get_json()
        archivo_path = data.get('archivo_path')
        assemblyai_key = data.get('assemblyai_key')
        
        if not archivo_path or not assemblyai_key:
            return jsonify({'success': False, 'error': 'archivo_path y assemblyai_key son requeridos'}), 400
        
        if not os.path.exists(archivo_path):
            return jsonify({'success': False, 'error': 'El archivo no existe'}), 404
        
        # Procesar audio usando la función existente
        from utils import procesar_audio_individual
        transcripcion, error, hash_archivo = procesar_audio_individual(archivo_path, assemblyai_key)
        
        if error:
            return jsonify({'success': False, 'error': error}), 500
        
        # Guardar en la base de datos
        try:
            from models import Transcripcion
            nueva_transcripcion = Transcripcion(
                archivo_original=os.path.basename(archivo_path),
                hash_archivo=hash_archivo,
                transcripcion_texto=transcripcion,
                usuario_correccion_id=current_user.id
            )
            db.session.add(nueva_transcripcion)
            db.session.commit()
        except Exception as e:
            print(f"Error al guardar transcripción en BD: {e}")
            # No fallar si no se puede guardar en BD
        
        # Log del evento
        utils.log_evento(
            'AUDIO_TRANSCRITO',
            f'Audio transcrito: {os.path.basename(archivo_path)}',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'archivo': os.path.basename(archivo_path), 'hash': hash_archivo}
        )
        
        return jsonify({
            'success': True,
            'transcripcion': transcripcion,
            'hash': hash_archivo,
            'archivo': os.path.basename(archivo_path)
        })
        
    except Exception as e:
        print(f"Error transcribiendo audio: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@transcripcion_bp.route('/api/upload-audio', methods=['POST'])
@login_required
def upload_audio():
    """Sube un archivo de audio al servidor"""
    try:
        if 'archivo' not in request.files:
            return jsonify({'success': False, 'error': 'No se encontró archivo'}), 400
        
        file = request.files['archivo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        # Obtener expediente y sesion_id si están disponibles
        expediente = request.form.get('expediente', '')
        sesion_id = request.form.get('sesion_id', '')
        
        # Determinar directorio de destino
        if sesion_id and expediente:
            # Usar estructura del expediente
            from config import Config
            audio_dir = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id, 'archivos_aportados')
        else:
            # Fallback a directorio general de audios
            from config import Config
            audio_dir = os.path.join(Config.BASE_UPLOAD_FOLDER, 'audios')
        
        os.makedirs(audio_dir, exist_ok=True)
        
        # Generar nombre seguro para el archivo
        from utils import generar_nombre_archivo_seguro
        nombre_archivo = generar_nombre_archivo_seguro(file.filename)
        ruta_archivo = os.path.join(audio_dir, nombre_archivo)
        
        # Guardar archivo
        file.save(ruta_archivo)
        
        # Calcular hash
        hash_archivo = utils.calcular_hash_sha256(ruta_archivo)
        
        # Log del evento
        utils.log_evento(
            'AUDIO_SUBIDO',
            f'Audio subido: {nombre_archivo}',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'archivo': nombre_archivo, 'hash': hash_archivo}
        )
        
        return jsonify({
            'success': True,
            'archivo': nombre_archivo,
            'ruta': ruta_archivo,
            'hash': hash_archivo,
            'tamaño': os.path.getsize(ruta_archivo)
        })
        
    except Exception as e:
        print(f"Error subiendo audio: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@transcripcion_bp.route('/api/upload-chat', methods=['POST'])
@login_required
def upload_chat():
    """Sube un archivo de chat al servidor"""
    try:
        if 'archivo' not in request.files:
            return jsonify({'success': False, 'error': 'No se encontró archivo'}), 400
        
        file = request.files['archivo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        # Obtener sesion_id si está disponible
        sesion_id = request.form.get('sesion_id', '')
        
        # Determinar directorio de destino
        if sesion_id:
            from config import Config
            chat_dir = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id, 'archivos_aportados')
        else:
            from config import Config
            chat_dir = os.path.join(Config.BASE_UPLOAD_FOLDER, 'chats')
        
        os.makedirs(chat_dir, exist_ok=True)
        
        # Generar nombre seguro para el archivo
        from utils import generar_nombre_archivo_seguro
        nombre_archivo = generar_nombre_archivo_seguro(file.filename)
        ruta_archivo = os.path.join(chat_dir, nombre_archivo)
        
        # Guardar archivo
        file.save(ruta_archivo)
        
        # Calcular hash
        hash_archivo = utils.calcular_hash_sha256(ruta_archivo)
        
        # Log del evento
        utils.log_evento(
            'CHAT_SUBIDO',
            f'Chat subido: {nombre_archivo}',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'archivo': nombre_archivo, 'hash': hash_archivo}
        )
        
        return jsonify({
            'success': True,
            'archivo': nombre_archivo,
            'ruta': ruta_archivo,
            'hash': hash_archivo,
            'tamaño': os.path.getsize(ruta_archivo)
        })
        
    except Exception as e:
        print(f"Error subiendo chat: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@transcripcion_bp.route('/api/upload-archivo-caso', methods=['POST'])
@login_required
def upload_archivo_caso():
    """Sube un archivo a un caso específico"""
    try:
        if 'archivo' not in request.files:
            return jsonify({'success': False, 'error': 'No se encontró archivo'}), 400
        
        file = request.files['archivo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        # Obtener datos del caso
        sesion_id = request.form.get('sesion_id')
        caso_id = request.form.get('caso_id')
        
        if not sesion_id or not caso_id:
            return jsonify({'success': False, 'error': 'sesion_id y caso_id son requeridos'}), 400
        
        # Verificar que el caso existe y pertenece al usuario
        from models import Caso
        caso = Caso.query.filter_by(sesion_id=sesion_id, id=caso_id).first()
        if not caso:
            return jsonify({'success': False, 'error': 'Caso no encontrado'}), 404
        
        if caso.usuario_id != current_user.id and not current_user.es_admin:
            return jsonify({'success': False, 'error': 'No tienes permisos para este caso'}), 403
        
        # Determinar directorio de destino
        from config import Config
        archivo_dir = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id, 'archivos_aportados')
        os.makedirs(archivo_dir, exist_ok=True)
        
        # Generar nombre seguro para el archivo
        from utils import generar_nombre_archivo_seguro, clasificar_tipo_archivo
        nombre_archivo = generar_nombre_archivo_seguro(file.filename)
        ruta_archivo = os.path.join(archivo_dir, nombre_archivo)
        
        # Guardar archivo
        file.save(ruta_archivo)
        
        # Calcular hash y clasificar tipo
        hash_archivo = utils.calcular_hash_sha256(ruta_archivo)
        tipo_archivo = utils.clasificar_tipo_archivo(nombre_archivo)
        
        # Guardar en la base de datos
        from models import ArchivoCaso
        nuevo_archivo = ArchivoCaso(
            nombre_original=file.filename,
            nombre_archivo=nombre_archivo,
            ruta_archivo=ruta_archivo,
            hash_sha256=hash_archivo,
            tipo_archivo=tipo_archivo,
            tamaño_bytes=os.path.getsize(ruta_archivo),
            caso_id=caso.id
        )
        db.session.add(nuevo_archivo)
        db.session.commit()
        
        # Log del evento
        utils.log_evento(
            'ARCHIVO_SUBIDO_CASO',
            f'Archivo subido al caso: {nombre_archivo}',
            current_user.id,
            request.remote_addr,
            request.headers.get('User-Agent'),
            {'archivo': nombre_archivo, 'caso_id': caso_id, 'hash': hash_archivo}
        )
        
        return jsonify({
            'success': True,
            'archivo': {
                'id': nuevo_archivo.id,
                'nombre_original': file.filename,
                'nombre_archivo': nombre_archivo,
                'tipo_archivo': tipo_archivo,
                'tamaño_bytes': os.path.getsize(ruta_archivo),
                'hash': hash_archivo
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error subiendo archivo al caso: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
