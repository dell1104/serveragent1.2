"""
Módulo para adquisición forense de imágenes
Soporta DD, E01, AFF4 usando librerías especializadas
"""

import os
import sys
import time
import hashlib
import threading
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional, Callable

class ForensicAcquisition:
    """Clase para manejar adquisición forense de imágenes"""
    
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.chunk_size = 1024 * 1024  # 1MB chunks
        self.progress_callback = None
        self.cancel_requested = False
        
    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """Establece callback para reportar progreso"""
        self.progress_callback = callback
    
    def cancel_acquisition(self):
        """Cancela la adquisición en progreso"""
        self.cancel_requested = True
    
    def _report_progress(self, current: int, total: int, status: str):
        """Reporta progreso si hay callback"""
        if self.progress_callback:
            self.progress_callback(current, total, status)
    
    def _validate_device_access(self, device_path: str) -> bool:
        """Valida que se puede acceder al dispositivo"""
        try:
            if self.is_windows:
                # En Windows, verificar que el dispositivo existe
                if not device_path.startswith("\\\\.\\"):
                    return False
                # Intentar abrir el dispositivo
                with open(device_path, 'rb') as f:
                    f.read(512)  # Leer un sector
                return True
            else:
                # En Linux, verificar que el dispositivo existe
                return os.path.exists(device_path)
        except (PermissionError, FileNotFoundError, OSError):
            return False
    
    def acquire_dd_image(self, device_path: str, output_path: str, 
                        verify_hash: bool = True, 
                        hash_algorithm: str = "md5") -> Dict:
        """
        Adquiere imagen DD (raw) usando Python puro
        
        Args:
            device_path: Ruta del dispositivo (ej: \\\\.\\PhysicalDrive0)
            output_path: Ruta de salida (ej: C:\imagen.dd)
            verify_hash: Si calcular hash durante la adquisición
            hash_algorithm: Algoritmo de hash (md5, sha1, sha256)
        
        Returns:
            Dict con resultado de la adquisición
        """
        start_time = time.time()
        result = {
            'success': False,
            'error': None,
            'duration': 0,
            'size': 0,
            'hash': None,
            'command': f"Python DD acquisition from {device_path}"
        }
        
        try:
            # Validar acceso al dispositivo
            if not self._validate_device_access(device_path):
                result['error'] = f"No se puede acceder al dispositivo: {device_path}"
                return result
            
            # Preparar archivo de salida
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Inicializar hash si se requiere
            hash_obj = None
            if verify_hash:
                if hash_algorithm == "md5":
                    hash_obj = hashlib.md5()
                elif hash_algorithm == "sha1":
                    hash_obj = hashlib.sha1()
                elif hash_algorithm == "sha256":
                    hash_obj = hashlib.sha256()
                else:
                    hash_obj = hashlib.md5()  # Default a MD5
            
            # Obtener tamaño del dispositivo
            device_size = self._get_device_size(device_path)
            if device_size == 0:
                result['error'] = "No se pudo determinar el tamaño del dispositivo"
                return result
            
            # Iniciar adquisición
            self._report_progress(0, device_size, "Iniciando adquisición DD...")
            
            with open(device_path, 'rb') as device:
                with open(output_path, 'wb') as output:
                    bytes_read = 0
                    
                    while bytes_read < device_size and not self.cancel_requested:
                        # Leer chunk
                        chunk = device.read(self.chunk_size)
                        if not chunk:
                            break
                        
                        # Escribir chunk
                        output.write(chunk)
                        
                        # Actualizar hash
                        if hash_obj:
                            hash_obj.update(chunk)
                        
                        # Actualizar progreso
                        bytes_read += len(chunk)
                        self._report_progress(
                            bytes_read, 
                            device_size, 
                            f"Adquiriendo... {bytes_read // (1024*1024)} MB"
                        )
            
            if self.cancel_requested:
                result['error'] = "Adquisición cancelada por el usuario"
                return result
            
            # Finalizar
            end_time = time.time()
            result.update({
                'success': True,
                'duration': end_time - start_time,
                'size': bytes_read,
                'hash': hash_obj.hexdigest() if hash_obj else None
            })
            
            self._report_progress(device_size, device_size, "Adquisición DD completada")
            
        except Exception as e:
            result['error'] = f"Error durante adquisición DD: {str(e)}"
        
        return result
    
    def acquire_e01_image(self, device_path: str, output_path: str,
                         compression: bool = True,
                         verify_hash: bool = True) -> Dict:
        """
        Adquiere imagen E01 usando ewfacquire
        
        Args:
            device_path: Ruta del dispositivo
            output_path: Ruta de salida (sin extensión)
            compression: Si usar compresión
            verify_hash: Si calcular hash
        
        Returns:
            Dict con resultado de la adquisición
        """
        start_time = time.time()
        result = {
            'success': False,
            'error': None,
            'duration': 0,
            'size': 0,
            'hash': None,
            'command': None
        }
        
        try:
            # Construir comando ewfacquire
            cmd = ['ewfacquire', '-t', output_path, device_path]
            
            if compression:
                cmd.extend(['-c', 'best'])
            else:
                cmd.extend(['-c', 'none'])
            
            if verify_hash:
                cmd.extend(['-H', 'md5'])
            
            result['command'] = ' '.join(cmd)
            
            # Ejecutar comando
            self._report_progress(0, 100, "Iniciando adquisición E01...")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitorear progreso
            while process.poll() is None and not self.cancel_requested:
                # Leer salida para detectar progreso
                line = process.stdout.readline()
                if line:
                    # Buscar indicadores de progreso en la salida
                    if "Progress:" in line or "%" in line:
                        self._report_progress(50, 100, f"E01: {line.strip()}")
                time.sleep(0.1)
            
            if self.cancel_requested:
                process.terminate()
                result['error'] = "Adquisición cancelada por el usuario"
                return result
            
            # Esperar a que termine
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                end_time = time.time()
                result.update({
                    'success': True,
                    'duration': end_time - start_time,
                    'size': self._get_file_size(output_path + ".E01"),
                    'hash': self._extract_hash_from_output(stdout)
                })
                self._report_progress(100, 100, "Adquisición E01 completada")
            else:
                result['error'] = f"Error en ewfacquire: {stderr}"
        
        except FileNotFoundError:
            result['error'] = "ewfacquire no está instalado. Instale libewf-tools"
        except Exception as e:
            result['error'] = f"Error durante adquisición E01: {str(e)}"
        
        return result
    
    def acquire_aff4_image(self, device_path: str, output_path: str,
                          compression: str = "deflate",
                          verify_hash: bool = True) -> Dict:
        """
        Adquiere imagen AFF4 usando pyaff4
        
        Args:
            device_path: Ruta del dispositivo
            output_path: Ruta de salida
            compression: Tipo de compresión (deflate, snappy, none)
            verify_hash: Si calcular hash
        
        Returns:
            Dict con resultado de la adquisición
        """
        start_time = time.time()
        result = {
            'success': False,
            'error': None,
            'duration': 0,
            'size': 0,
            'hash': None,
            'command': "Python AFF4 acquisition"
        }
        
        try:
            # Importar pyaff4
            try:
                from pyaff4 import aff4
                from pyaff4 import rdfvalue
                from pyaff4 import lexicon
            except ImportError:
                result['error'] = "pyaff4 no está instalado. Ejecute: pip install pyaff4"
                return result
            
            # Crear volumen AFF4
            with aff4.AFF4Volume.createNewVolume(output_path) as volume:
                # Configurar metadatos
                volume.set(lexicon.AFF4_STORED, rdfvalue.URN(device_path))
                volume.set(lexicon.AFF4_CREATION_TIME, rdfvalue.XSDDateTime(time.time()))
                
                # Crear stream de datos
                with volume.createMember(device_path) as stream:
                    # Configurar compresión
                    if compression != "none":
                        stream.set(lexicon.AFF4_IMAGE_COMPRESSION, rdfvalue.URN(compression))
                    
                    # Leer dispositivo y escribir a AFF4
                    device_size = self._get_device_size(device_path)
                    bytes_read = 0
                    
                    with open(device_path, 'rb') as device:
                        while bytes_read < device_size and not self.cancel_requested:
                            chunk = device.read(self.chunk_size)
                            if not chunk:
                                break
                            
                            stream.write(chunk)
                            bytes_read += len(chunk)
                            
                            self._report_progress(
                                bytes_read,
                                device_size,
                                f"AFF4: {bytes_read // (1024*1024)} MB"
                            )
            
            if self.cancel_requested:
                result['error'] = "Adquisición cancelada por el usuario"
                return result
            
            end_time = time.time()
            result.update({
                'success': True,
                'duration': end_time - start_time,
                'size': bytes_read,
                'hash': self._calculate_file_hash(output_path, "md5") if verify_hash else None
            })
            
            self._report_progress(device_size, device_size, "Adquisición AFF4 completada")
        
        except Exception as e:
            result['error'] = f"Error durante adquisición AFF4: {str(e)}"
        
        return result
    
    def _get_device_size(self, device_path: str) -> int:
        """Obtiene el tamaño del dispositivo en bytes"""
        try:
            if self.is_windows:
                # En Windows, usar wmic para obtener el tamaño
                device_id = device_path.replace("\\\\.\\", "")
                result = subprocess.run([
                    'wmic', 'diskdrive', 'where', 
                    f'DeviceID="{device_id}"',
                    'get', 'Size', '/format:csv'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # Saltar encabezado
                        if line.strip():
                            parts = line.split(',')
                            if len(parts) >= 2 and parts[1].strip().isdigit():
                                return int(parts[1].strip())
            else:
                # En Linux, usar fdisk
                result = subprocess.run([
                    'fdisk', '-l', device_path
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Parsear salida de fdisk para obtener tamaño
                    for line in result.stdout.split('\n'):
                        if device_path in line and 'bytes' in line:
                            # Extraer tamaño de la línea
                            import re
                            match = re.search(r'(\d+)\s+bytes', line)
                            if match:
                                return int(match.group(1))
            
            return 0
        except:
            return 0
    
    def _get_file_size(self, file_path: str) -> int:
        """Obtiene el tamaño de un archivo"""
        try:
            return os.path.getsize(file_path)
        except:
            return 0
    
    def _calculate_file_hash(self, file_path: str, algorithm: str = "md5") -> str:
        """Calcula hash de un archivo"""
        try:
            hash_obj = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except:
            return ""
    
    def _extract_hash_from_output(self, output: str) -> str:
        """Extrae hash de la salida de ewfacquire"""
        try:
            import re
            # Buscar hash MD5 en la salida
            match = re.search(r'MD5\s+hash\s+calculated\s+as:\s+([a-f0-9]+)', output, re.IGNORECASE)
            if match:
                return match.group(1)
        except:
            pass
        return ""

# Función de conveniencia para usar la clase
def acquire_forensic_image(device_path: str, output_path: str, 
                          format_type: str = "DD",
                          **kwargs) -> Dict:
    """
    Función de conveniencia para adquirir imagen forense
    
    Args:
        device_path: Ruta del dispositivo
        output_path: Ruta de salida
        format_type: Tipo de formato (DD, E01, AFF4)
        **kwargs: Argumentos adicionales
    
    Returns:
        Dict con resultado de la adquisición
    """
    acquirer = ForensicAcquisition()
    
    if format_type.upper() == "DD":
        return acquirer.acquire_dd_image(device_path, output_path, **kwargs)
    elif format_type.upper() == "E01":
        return acquirer.acquire_e01_image(device_path, output_path, **kwargs)
    elif format_type.upper() == "AFF4":
        return acquirer.acquire_aff4_image(device_path, output_path, **kwargs)
    else:
        return {
            'success': False,
            'error': f"Formato no soportado: {format_type}"
        }
