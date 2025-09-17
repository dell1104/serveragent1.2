# utils.py
import os
import hashlib
import datetime
import json
import re
import magic  # Para validación de tipos MIME
from werkzeug.utils import secure_filename
from config import Config

def calcular_hash_sha256(archivo_path):
    """Calcula el hash SHA256 de un archivo"""
    hash_sha256 = hashlib.sha256()
    try:
        with open(archivo_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        print(f"Error calculando hash: {e}")
        return None

def calcular_hash_sha256_from_bytes(contenido, algoritmo='sha256'):
    """Calcula el hash de contenido en bytes usando el algoritmo especificado"""
    try:
        if algoritmo.lower() == 'md5':
            hash_obj = hashlib.md5()
        elif algoritmo.lower() == 'sha1':
            hash_obj = hashlib.sha1()
        elif algoritmo.lower() == 'sha256':
            hash_obj = hashlib.sha256()
        elif algoritmo.lower() == 'sha512':
            hash_obj = hashlib.sha512()
        else:
            hash_obj = hashlib.sha256()  # Por defecto SHA256
        
        hash_obj.update(contenido)
        return hash_obj.hexdigest().upper()
    except Exception as e:
        print(f"Error calculando hash: {e}")
        return None

def obtener_extension_archivo(nombre_archivo):
    """Obtiene la extensión de un archivo"""
    return os.path.splitext(nombre_archivo)[1].lower().lstrip('.')

def clasificar_tipo_archivo(extension):
    """Clasifica un archivo según su extensión"""
    for tipo, extensiones in Config.ALLOWED_EXTENSIONS.items():
        if extension in extensiones:
            return tipo
    return 'documento'  # Por defecto

def crear_estructura_caso(sesion_id, expediente, oficina_fiscal):
    """Crea la estructura de carpetas para un caso"""
    try:
        # Usar sesion_id directamente sin sanitizar para mantener el formato correcto
        carpeta_caso = os.path.join(Config.BASE_UPLOAD_FOLDER, sesion_id)
        print(f"📁 Creando carpeta: {carpeta_caso}")  # Debug log
        os.makedirs(carpeta_caso, exist_ok=True)
        
        # Crear subcarpetas
        subcarpetas = [
            'acta',
            'informe_tecnico', 
            'archivos_aportados',
            'evidencia_en_proceso'
        ]
        
        for subcarpeta in subcarpetas:
            ruta_subcarpeta = os.path.join(carpeta_caso, subcarpeta)
            os.makedirs(ruta_subcarpeta, exist_ok=True)
            print(f"📂 Subcarpeta creada: {ruta_subcarpeta}")  # Debug log
        
        print(f"✅ Estructura creada exitosamente: {carpeta_caso}")  # Debug log
        return carpeta_caso
    except Exception as e:
        print(f"Error creando estructura de caso: {e}")
        return None

def generar_nombre_archivo_seguro(nombre_original, prefijo=""):
    """Genera un nombre de archivo seguro"""
    nombre_base, extension = os.path.splitext(nombre_original)
    nombre_seguro = secure_filename(nombre_base)
    
    if prefijo:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefijo}_{nombre_seguro}_{timestamp}{extension}"
    else:
        return f"{nombre_seguro}{extension}"

def guardar_hash_archivo(archivo_path, hash_sha256, carpeta_destino):
    """Guarda el hash de un archivo en un archivo TXT consolidado por caso"""
    try:
        nombre_archivo = os.path.basename(archivo_path)
        fecha_calculo = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Crear contenido del archivo de hash
        contenido_hash = f"ARCHIVO: {nombre_archivo}\n"
        contenido_hash += f"HASH SHA256: {hash_sha256}\n"
        contenido_hash += f"FECHA DE CÁLCULO: {fecha_calculo}\n"
        contenido_hash += f"TAMAÑO: {os.path.getsize(archivo_path)} bytes\n"
        contenido_hash += "-" * 50 + "\n"
        
        # Usar un nombre fijo para el archivo de hashes del caso
        archivo_hash_path = os.path.join(carpeta_destino, "hashes_caso.txt")
        
        # Verificar si el archivo ya existe para agregar encabezado
        archivo_existe = os.path.exists(archivo_hash_path)
        
        with open(archivo_hash_path, 'a', encoding='utf-8') as f:
            # Si es el primer archivo, agregar encabezado
            if not archivo_existe:
                f.write("=" * 80 + "\n")
                f.write("REGISTRO DE HASHES DEL CASO\n")
                f.write("=" * 80 + "\n")
                f.write(f"FECHA DE CREACIÓN: {fecha_calculo}\n")
                f.write(f"CARPETA: {carpeta_destino}\n")
                f.write("=" * 80 + "\n\n")
            
            f.write(contenido_hash)
        
        return archivo_hash_path
    except Exception as e:
        print(f"Error guardando hash: {e}")
        return None

def parsear_transcripciones_txt(contenido_txt):
    """Parsea un archivo TXT de transcripciones y devuelve estadísticas y datos"""
    import re
    
    # Contar tags para estadísticas
    count_no_verificadas = len(re.findall(r'TAG: NO_VERIFICADO', contenido_txt))
    count_verificadas = len(re.findall(r'TAG: VERIFICADO', contenido_txt))
    
    # Dividir el contenido en bloques de transcripción
    bloques = re.split(r'\n={80}\n', contenido_txt)
    matches = []
    
    for bloque in bloques:
        if 'TAG: NO_VERIFICADO' in bloque:
            # Extraer datos del bloque
            archivo_match = re.search(r'ARCHIVO: (.+)', bloque)
            hash_match = re.search(r'HASH SHA256: (.+)', bloque)
            transcripcion_match = re.search(r'-{50}\n(.*?)(?=\n\n|\Z)', bloque, re.DOTALL)
            
            if archivo_match and hash_match and transcripcion_match:
                matches.append((
                    archivo_match.group(1).strip(),
                    hash_match.group(1).strip(),
                    transcripcion_match.group(1).strip()
                ))
    
    return {
        'estadisticas': {
            'corregidas': count_verificadas,
            'no_corregidas': count_no_verificadas,
            'total': count_verificadas + count_no_verificadas
        },
        'transcripciones': matches
    }

def log_evento(tipo, descripcion, usuario_id=None, ip_address=None, user_agent=None, datos_adicionales=None):
    """Registra un evento en el log del sistema"""
    try:
        # Importar aquí para evitar imports circulares
        from models import LogEvento, db
        
        evento = LogEvento(
            tipo_evento=tipo,
            descripcion=descripcion,
            usuario_id=usuario_id,
            ip_address=ip_address,
            user_agent=user_agent,
            datos_adicionales=datos_adicionales
        )
        
        db.session.add(evento)
        db.session.commit()
        
        return True
    except Exception as e:
        print(f"Error registrando evento: {e}")
        return False

def validar_archivo_audio(nombre_archivo):
    """Valida si un archivo es de audio válido"""
    extension = obtener_extension_archivo(nombre_archivo)
    return extension in Config.ALLOWED_EXTENSIONS['audio']

def obtener_tamaño_archivo_formateado(ruta_archivo):
    """Obtiene el tamaño de un archivo en formato legible"""
    try:
        tamaño_bytes = os.path.getsize(ruta_archivo)
        
        if tamaño_bytes < 1024:
            return f"{tamaño_bytes} B"
        elif tamaño_bytes < 1024 * 1024:
            return f"{tamaño_bytes / 1024:.1f} KB"
        elif tamaño_bytes < 1024 * 1024 * 1024:
            return f"{tamaño_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{tamaño_bytes / (1024 * 1024 * 1024):.1f} GB"
    except Exception:
        return "Desconocido"

def procesar_audio_individual(archivo_path, assemblyai_key):
    """Procesa un archivo de audio individual con AssemblyAI"""
    try:
        import requests
        
        # Calcular hash del archivo
        hash_archivo = calcular_hash_sha256(archivo_path)
        if not hash_archivo:
            return None, "Error calculando hash del archivo", None
        
        # Subir archivo a AssemblyAI
        headers = {"authorization": assemblyai_key}
        
        with open(archivo_path, "rb") as f:
            response = requests.post("https://api.assemblyai.com/v2/upload", headers=headers, data=f)
        
        if response.status_code != 200:
            return None, f"Error subiendo archivo: {response.text}", hash_archivo
        
        audio_url = response.json()["upload_url"]
        
        # Configurar transcripción
        data = {
            "audio_url": audio_url,
            "language_code": "es",
            "speaker_labels": True
        }
        
        response = requests.post("https://api.assemblyai.com/v2/transcript", json=data, headers=headers)
        
        if response.status_code != 200:
            return None, f"Error iniciando transcripción: {response.text}", hash_archivo
        
        transcript_id = response.json()['id']
        
        # Polling para obtener resultado
        polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        
        while True:
            transcription_result = requests.get(polling_endpoint, headers=headers).json()
            
            if transcription_result['status'] == 'completed':
                transcripcion_texto = transcription_result['text']
                return transcripcion_texto, None, hash_archivo
            elif transcription_result['status'] == 'error':
                return None, f"Error en transcripción: {transcription_result.get('error', 'Error desconocido')}", hash_archivo
            
            # Esperar 1 segundo antes del siguiente polling
            import time
            time.sleep(1)
            
    except Exception as e:
        return None, f"Error procesando audio: {str(e)}", None

# ===== FUNCIONES DE SEGURIDAD MEJORADAS =====

def validar_archivo_seguro(archivo, max_size_mb=50):
    """
    Valida un archivo de forma segura antes de guardarlo
    
    Args:
        archivo: Archivo de Flask request.files
        max_size_mb: Tamaño máximo en MB
    
    Returns:
        tuple: (es_valido, mensaje_error, tipo_mime_real)
    """
    try:
        # 1. Verificar que el archivo existe y tiene nombre
        if not archivo or not archivo.filename:
            return False, "No se seleccionó ningún archivo", None
        
        # 2. Verificar tamaño del archivo
        archivo.seek(0, 2)  # Ir al final del archivo
        tamaño_bytes = archivo.tell()
        archivo.seek(0)  # Volver al inicio
        
        max_size_bytes = max_size_mb * 1024 * 1024
        if tamaño_bytes > max_size_bytes:
            return False, f"El archivo es demasiado grande. Máximo permitido: {max_size_mb}MB", None
        
        # 3. Verificar que el archivo no esté vacío
        if tamaño_bytes == 0:
            return False, "El archivo está vacío", None
        
        # 4. Obtener nombre seguro
        nombre_original = archivo.filename
        nombre_seguro = secure_filename(nombre_original)
        
        if not nombre_seguro or nombre_seguro != nombre_original:
            return False, "Nombre de archivo no válido o inseguro", None
        
        # 5. Validar extensión
        extension = obtener_extension_archivo(nombre_original)
        if not extension:
            return False, "Archivo sin extensión", None
        
        # 6. Verificar que la extensión esté permitida
        tipo_archivo = clasificar_tipo_archivo(extension)
        if not tipo_archivo:
            return False, f"Tipo de archivo no permitido: {extension}", None
        
        # 7. Validar tipo MIME real del archivo (verificación adicional)
        try:
            archivo.seek(0)
            contenido = archivo.read(1024)  # Leer solo los primeros 1KB
            archivo.seek(0)  # Volver al inicio
            
            tipo_mime_real = magic.from_buffer(contenido, mime=True)
            
            # Mapeo de extensiones a tipos MIME esperados
            mime_esperados = {
                'audio': ['audio/mpeg', 'audio/wav', 'audio/mp3', 'audio/ogg', 'audio/m4a'],
                'video': ['video/mp4', 'video/avi', 'video/mov', 'video/wmv', 'video/quicktime'],
                'image': ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff'],
                'document': ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
            }
            
            if tipo_mime_real not in mime_esperados.get(tipo_archivo, []):
                return False, f"El tipo de archivo no coincide con la extensión. Esperado: {tipo_archivo}, Detectado: {tipo_mime_real}", None
                
        except Exception as e:
            print(f"Advertencia: No se pudo validar tipo MIME: {e}")
            # Continuar sin validación MIME si hay error
        
        return True, "Archivo válido", tipo_mime_real
        
    except Exception as e:
        return False, f"Error validando archivo: {str(e)}", None

def sanitizar_input_usuario(texto, max_length=500):
    """
    Sanitiza input del usuario para prevenir XSS y otros ataques
    
    Args:
        texto: Texto a sanitizar
        max_length: Longitud máxima permitida
    
    Returns:
        str: Texto sanitizado
    """
    if not texto:
        return ""
    
    # 1. Limitar longitud
    texto = str(texto)[:max_length]
    
    # 2. Eliminar caracteres peligrosos
    caracteres_peligrosos = ['<', '>', '"', "'", '&', ';', '(', ')', 'script', 'javascript', 'vbscript']
    for char in caracteres_peligrosos:
        texto = texto.replace(char, '')
    
    # 3. Eliminar espacios extra
    texto = ' '.join(texto.split())
    
    return texto.strip()

def validar_expediente(expediente):
    """
    Valida formato de expediente
    
    Args:
        expediente: Número de expediente a validar
    
    Returns:
        tuple: (es_valido, mensaje_error)
    """
    if not expediente:
        return False, "Expediente requerido"
    
    # Patrón para expedientes: P-12345/25, T-67890/25, etc.
    patron_expediente = r'^[A-Za-z]+-\d{4,7}/\d{2}$'
    
    if not re.match(patron_expediente, expediente.strip()):
        return False, "Formato de expediente inválido. Use: P-1234567/25 (4-7 dígitos)"
    
    return True, "Expediente válido"

def log_seguridad(evento, detalles, ip_address, user_agent):
    """
    Registra eventos de seguridad
    
    Args:
        evento: Tipo de evento de seguridad
        detalles: Detalles del evento
        ip_address: IP del usuario
        user_agent: User agent del navegador
    """
    try:
        from models import LogEvento, db
        
        log = LogEvento(
            tipo_evento=f"SECURITY_{evento}",
            descripcion=detalles,
            ip_address=ip_address,
            user_agent=user_agent,
            datos_adicionales={
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'severity': 'HIGH' if 'ATTACK' in evento else 'MEDIUM'
            }
        )
        
        db.session.add(log)
        db.session.commit()
        
    except Exception as e:
        print(f"Error registrando evento de seguridad: {e}")
