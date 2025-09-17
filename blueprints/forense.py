import subprocess
import os
import json
import platform
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import utils
from utils_package.forensic_acquisition import ForensicAcquisition, acquire_forensic_image

forense_bp = Blueprint('forense', __name__)

@forense_bp.route('/api/detectar-dispositivos', methods=['GET'])
@login_required
def detectar_dispositivos():
    """Detecta dispositivos reales del sistema"""
    try:
        dispositivos = []
        
        if platform.system() == "Windows":
            # Usar wmic para detectar discos en Windows
            try:
                resultado = subprocess.run([
                    'wmic', 'diskdrive', 'get', 'DeviceID,Model,Size,InterfaceType', '/format:csv'
                ], capture_output=True, text=True, encoding='utf-8', timeout=10)
                
                if resultado.returncode == 0 and resultado.stdout.strip():
                    lineas = resultado.stdout.strip().split('\n')
                    for linea in lineas[1:]:  # Saltar encabezado
                        if linea.strip() and ',' in linea:
                            partes = linea.split(',')
                            if len(partes) >= 5:
                                device_id = partes[1].strip()
                                interface = partes[2].strip()
                                model = partes[3].strip()
                                size = partes[4].strip()
                                
                                if device_id and model:
                                    # Convertir tamaño de bytes a GB
                                    try:
                                        size_gb = int(size) // (1024**3) if size.isdigit() else 0
                                        size_str = f"{size_gb} GB" if size_gb > 0 else "N/A"
                                    except:
                                        size_str = "N/A"
                                    
                                    dispositivos.append({
                                        'ruta': device_id,  # Ya incluye \\\\.\\
                                        'nombre': f"{model} ({size_str})",
                                        'tipo': 'HDD' if 'SATA' in interface else 'USB',
                                        'tamano': size_str,
                                        'marca': model.split()[0] if model else 'N/A',
                                        'modelo': model,
                                        'interface': interface,
                                        'smart': {'estado': 'Disponible'}
                                    })
            except Exception as e:
                print(f"Error detectando dispositivos Windows: {e}")
                # Fallback: dispositivos simulados
                dispositivos = [
                    {
                        'ruta': '\\\\.\\PhysicalDrive0',
                        'nombre': 'Disco Principal (Simulado)',
                        'tipo': 'HDD',
                        'tamano': '500 GB',
                        'marca': 'Simulated',
                        'modelo': 'Test Drive',
                        'interface': 'SATA',
                        'smart': {'estado': 'Simulado'}
                    }
                ]
        else:
            # Usar lsblk para detectar discos en Linux
            try:
                resultado = subprocess.run(['lsblk', '-J'], capture_output=True, text=True, timeout=10)
                
                if resultado.returncode == 0:
                    data = json.loads(resultado.stdout)
                    for device in data.get('blockdevices', []):
                        if device.get('type') == 'disk':
                            dispositivos.append({
                                'ruta': f"/dev/{device['name']}",
                                'nombre': f"{device.get('model', 'Disco')} ({device.get('size', 'N/A')})",
                                'tipo': 'HDD' if 'ata' in device.get('name', '') else 'USB',
                                'tamano': device.get('size', 'N/A'),
                                'marca': device.get('vendor', 'N/A'),
                                'modelo': device.get('model', 'N/A'),
                                'smart': {'estado': 'Disponible'}
                            })
            except Exception as e:
                print(f"Error detectando dispositivos Linux: {e}")
                # Fallback: dispositivos simulados
                dispositivos = [
                    {
                        'ruta': '/dev/sda',
                        'nombre': 'Disco Principal (Simulado)',
                        'tipo': 'HDD',
                        'tamano': '500G',
                        'marca': 'Simulated',
                        'modelo': 'Test Drive',
                        'smart': {'estado': 'Simulado'}
                    }
                ]
        
        # Si no se detectaron dispositivos, usar fallback
        if not dispositivos:
            dispositivos = [
                {
                    'ruta': '\\\\.\\PhysicalDrive0' if platform.system() == "Windows" else '/dev/sda',
                    'nombre': 'Disco Principal (Fallback)',
                    'tipo': 'HDD',
                    'tamano': '500 GB',
                    'marca': 'Fallback',
                    'modelo': 'Test Drive',
                    'smart': {'estado': 'Fallback'}
                }
            ]
        
        return jsonify({'success': True, 'dispositivos': dispositivos})
        
    except Exception as e:
        print(f"Error general en detección: {e}")
        # Fallback final
        fallback_dispositivos = [
            {
                'ruta': '\\\\.\\PhysicalDrive0' if platform.system() == "Windows" else '/dev/sda',
                'nombre': 'Disco Principal (Fallback)',
                'tipo': 'HDD',
                'tamano': '500 GB',
                'marca': 'Fallback',
                'modelo': 'Test Drive',
                'smart': {'estado': 'Fallback'}
            }
        ]
        return jsonify({'success': True, 'dispositivos': fallback_dispositivos})

@forense_bp.route('/api/leer-smart', methods=['POST'])
@login_required
def leer_smart():
    """Lee datos SMART reales del dispositivo"""
    try:
        dispositivo = request.json.get('dispositivo')
        if not dispositivo:
            return jsonify({'success': False, 'error': 'Dispositivo no especificado'})
        
        smart_data = {}
        
        if platform.system() == "Windows":
            # Usar smartctl si está disponible
            try:
                resultado = subprocess.run([
                    'smartctl', '-a', dispositivo
                ], capture_output=True, text=True, timeout=30)
                
                if resultado.returncode == 0:
                    smart_data = parsear_smart_windows(resultado.stdout)
                else:
                    # Fallback: usar wmic para información básica
                    smart_data = obtener_info_basica_windows(dispositivo)
            except:
                smart_data = obtener_info_basica_windows(dispositivo)
        else:
            # Linux: usar smartctl
            try:
                resultado = subprocess.run([
                    'smartctl', '-a', dispositivo
                ], capture_output=True, text=True, timeout=30)
                
                if resultado.returncode == 0:
                    smart_data = parsear_smart_linux(resultado.stdout)
                else:
                    smart_data = {'estado': 'No disponible', 'error': 'smartctl no disponible'}
            except:
                smart_data = {'estado': 'Error', 'error': 'No se pudo leer SMART'}
        
        return jsonify({'success': True, 'smart': smart_data})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@forense_bp.route('/api/adquirir-imagen', methods=['POST'])
@login_required
def adquirir_imagen():
    """Ejecuta adquisición real de imagen forense"""
    try:
        dispositivo = request.json.get('dispositivo')
        destino = request.json.get('destino')
        formato = request.json.get('formato')
        verificacion_hash = request.json.get('verificacion_hash', True)
        compresion = request.json.get('compresion', False)
        
        if not all([dispositivo, destino, formato]):
            return jsonify({'success': False, 'error': 'Faltan parámetros requeridos'})
        
        # Validar formato
        formatos_validos = ['DD', 'E01', 'AFF4', 'IMG']
        if formato not in formatos_validos:
            return jsonify({'success': False, 'error': f'Formato {formato} no soportado'})
        
        # Usar el nuevo módulo de adquisición
        acquirer = ForensicAcquisition()
        
        # Configurar callback de progreso (opcional)
        def progress_callback(current, total, status):
            # Aquí podrías enviar actualizaciones via WebSocket o guardar en base de datos
            print(f"Progreso: {current}/{total} - {status}")
        
        acquirer.set_progress_callback(progress_callback)
        
        # Ejecutar adquisición según formato
        if formato in ['DD', 'IMG']:
            resultado = acquirer.acquire_dd_image(
                device_path=dispositivo,
                output_path=destino,
                verify_hash=verificacion_hash
            )
        elif formato == 'E01':
            resultado = acquirer.acquire_e01_image(
                device_path=dispositivo,
                output_path=destino,
                compression=compresion,
                verify_hash=verificacion_hash
            )
        elif formato == 'AFF4':
            resultado = acquirer.acquire_aff4_image(
                device_path=dispositivo,
                output_path=destino,
                compression='deflate' if compresion else 'none',
                verify_hash=verificacion_hash
            )
        
        # Log de la operación
        utils.SistemaLogging.log_forensic_acquisition(
            user_id=current_user.id,
            device=dispositivo,
            destination=destino,
            format=formato,
            command=resultado.get('command', 'Python acquisition')
        )
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def construir_comando_adquisicion(dispositivo, destino, formato, verificacion_hash, compresion):
    """Construye el comando de adquisición según el formato"""
    
    if formato == 'DD' or formato == 'IMG':
        # dc3dd para DD e IMG
        comando = f'dc3dd if={dispositivo} of={destino}'
        if verificacion_hash:
            comando += ' hash=md5'
        comando += f' log={destino}.log'
        return comando
    
    elif formato == 'E01':
        # ewfacquire para E01
        comando = f'ewfacquire -t {destino} {dispositivo}'
        if compresion:
            comando += ' -c best'
        if verificacion_hash:
            comando += ' -H md5'
        return comando
    
    elif formato == 'AFF':
        # Para AFF necesitamos herramientas adicionales
        # Por ahora, usar dc3dd y luego convertir
        comando = f'dc3dd if={dispositivo} of={destino}.dd hash=md5'
        return comando
    
    return None

def parsear_smart_windows(smart_output):
    """Parsea la salida de smartctl en Windows"""
    smart_data = {'estado': 'OK'}
    
    lineas = smart_output.split('\n')
    for linea in lineas:
        if 'Temperature' in linea and 'Celsius' in linea:
            temp = linea.split()[-2]
            smart_data['temperatura'] = f"{temp}°C"
        elif 'Power_On_Hours' in linea:
            horas = linea.split()[-1]
            smart_data['horasEncendido'] = horas
        elif 'Reallocated_Sector_Ct' in linea:
            sectores = linea.split()[-1]
            smart_data['sectoresReasignados'] = sectores
        elif 'Current_Pending_Sector' in linea:
            pendientes = linea.split()[-1]
            smart_data['sectoresPendientes'] = pendientes
    
    return smart_data

def parsear_smart_linux(smart_output):
    """Parsea la salida de smartctl en Linux"""
    smart_data = {'estado': 'OK'}
    
    lineas = smart_output.split('\n')
    for linea in lineas:
        if 'Temperature_Celsius' in linea:
            temp = linea.split()[-1]
            smart_data['temperatura'] = f"{temp}°C"
        elif 'Power_On_Hours' in linea:
            horas = linea.split()[-1]
            smart_data['horasEncendido'] = horas
        elif 'Reallocated_Sector_Ct' in linea:
            sectores = linea.split()[-1]
            smart_data['sectoresReasignados'] = sectores
    
    return smart_data

def obtener_info_basica_windows(dispositivo):
    """Obtiene información básica usando wmic cuando smartctl no está disponible"""
    try:
        # Limpiar el dispositivo antes de usarlo en el f-string
        dispositivo_limpio = dispositivo.replace("\\\\.\\", "")
        
        # Obtener información básica del disco
        resultado = subprocess.run([
            'wmic', 'diskdrive', 'where', f'DeviceID="{dispositivo_limpio}"',
            'get', 'Model,Size,Status', '/format:csv'
        ], capture_output=True, text=True)
        
        if resultado.returncode == 0:
            return {
                'estado': 'Básico',
                'info': 'Datos SMART no disponibles. Instale smartmontools para información completa.'
            }
    except:
        pass
    
    return {'estado': 'No disponible', 'error': 'No se pudo obtener información'}

@forense_bp.route('/api/calcular-hash', methods=['POST'])
@login_required
def calcular_hash():
    """Calcula hash de archivos enviados"""
    try:
        if 'archivos' not in request.files:
            return jsonify({'success': False, 'error': 'No se enviaron archivos'}), 400
        
        archivos = request.files.getlist('archivos')
        algoritmo = request.form.get('algoritmo', 'sha256')
        
        if not archivos or archivos[0].filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionaron archivos'}), 400
        
        resultados = []
        
        for archivo in archivos:
            if archivo.filename:
                # Leer el contenido del archivo
                contenido = archivo.read()
                archivo.seek(0)  # Resetear posición para futuras lecturas
                
                # Calcular hash usando la función de utils
                hash_resultado = utils.calcular_hash_sha256_from_bytes(contenido, algoritmo)
                
                resultados.append({
                    'nombre': archivo.filename,
                    'algoritmo': algoritmo.upper(),
                    'hash': hash_resultado,
                    'tamaño': len(contenido),
                    'fecha': utils.datetime.datetime.now().isoformat()
                })
        
        return jsonify({
            'success': True,
            'resultados': resultados,
            'total_archivos': len(resultados)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@forense_bp.route('/api/calcular-hash-carpeta', methods=['POST'])
@login_required
def calcular_hash_carpeta():
    """Calcula hash de todos los archivos en una carpeta"""
    try:
        data = request.get_json()
        ruta_carpeta = data.get('ruta_carpeta')
        algoritmo = data.get('algoritmo', 'sha256')
        recursivo = data.get('recursivo', False)
        
        if not ruta_carpeta:
            return jsonify({'success': False, 'error': 'Ruta de carpeta requerida'}), 400
        
        # Verificar que la carpeta existe
        if not os.path.exists(ruta_carpeta):
            return jsonify({'success': False, 'error': 'La carpeta no existe'}), 400
        
        if not os.path.isdir(ruta_carpeta):
            return jsonify({'success': False, 'error': 'La ruta no es una carpeta'}), 400
        
        resultados = []
        archivos_procesados = 0
        
        # Función para procesar archivos recursivamente
        def procesar_archivos(directorio):
            nonlocal archivos_procesados
            try:
                for item in os.listdir(directorio):
                    ruta_completa = os.path.join(directorio, item)
                    
                    if os.path.isfile(ruta_completa):
                        try:
                            # Calcular hash del archivo
                            with open(ruta_completa, 'rb') as f:
                                contenido = f.read()
                            
                            hash_resultado = utils.calcular_hash_sha256_from_bytes(contenido, algoritmo)
                            
                            resultados.append({
                                'nombre': item,
                                'ruta': ruta_completa,
                                'ruta_relativa': os.path.relpath(ruta_completa, ruta_carpeta),
                                'algoritmo': algoritmo.upper(),
                                'hash': hash_resultado,
                                'tamaño': len(contenido),
                                'fecha': utils.datetime.datetime.now().isoformat()
                            })
                            
                            archivos_procesados += 1
                            
                        except Exception as e:
                            print(f"Error procesando archivo {ruta_completa}: {e}")
                            continue
                    
                    elif os.path.isdir(ruta_completa) and recursivo:
                        procesar_archivos(ruta_completa)
                        
            except Exception as e:
                print(f"Error procesando directorio {directorio}: {e}")
        
        # Procesar la carpeta
        procesar_archivos(ruta_carpeta)
        
        return jsonify({
            'success': True,
            'resultados': resultados,
            'total_archivos': archivos_procesados,
            'carpeta': ruta_carpeta,
            'recursivo': recursivo
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
