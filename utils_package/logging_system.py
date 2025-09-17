# utils/logging_system.py
from flask import request, current_app
from flask_login import current_user
from models import db, LogEvento
from datetime import datetime
import json

class SistemaLogging:
    """Sistema centralizado de logging para el sistema forense"""
    
    # Categorías de eventos
    CATEGORIAS = {
        'AUTH': 'Autenticación',
        'USER': 'Gestión de Usuarios', 
        'CASE': 'Gestión de Casos',
        'FILE': 'Gestión de Archivos',
        'TRANSCRIPT': 'Transcripciones',
        'ADMIN': 'Administración',
        'SECURITY': 'Seguridad',
        'SYSTEM': 'Sistema',
        'BACKUP': 'Respaldo',
        'EXPORT': 'Exportación'
    }
    
    # Tipos de eventos específicos
    EVENTOS = {
        # Autenticación
        'LOGIN_SUCCESS': 'Inicio de sesión exitoso',
        'LOGIN_FAILED': 'Intento de inicio de sesión fallido',
        'LOGOUT': 'Cierre de sesión',
        'PASSWORD_CHANGE': 'Cambio de contraseña',
        'PASSWORD_RESET': 'Restablecimiento de contraseña',
        
        # Gestión de Usuarios
        'USER_CREATE': 'Creación de usuario',
        'USER_UPDATE': 'Actualización de usuario',
        'USER_DELETE': 'Eliminación de usuario',
        'USER_ACTIVATE': 'Activación de usuario',
        'USER_DEACTIVATE': 'Desactivación de usuario',
        'USER_ROLE_CHANGE': 'Cambio de rol de usuario',
        
        # Gestión de Casos
        'CASE_CREATE': 'Creación de caso',
        'CASE_UPDATE': 'Actualización de caso',
        'CASE_DELETE': 'Eliminación de caso',
        'CASE_VIEW': 'Visualización de caso',
        'CASE_COMPLETE': 'Finalización de caso',
        'CASE_ARCHIVE': 'Archivado de caso',
        
        # Gestión de Archivos
        'FILE_UPLOAD': 'Carga de archivo',
        'FILE_DOWNLOAD': 'Descarga de archivo',
        'FILE_DELETE': 'Eliminación de archivo',
        'FILE_VIEW': 'Visualización de archivo',
        
        # Transcripciones
        'TRANSCRIPT_START': 'Inicio de transcripción',
        'TRANSCRIPT_COMPLETE': 'Transcripción completada',
        'TRANSCRIPT_ERROR': 'Error en transcripción',
        'TRANSCRIPT_CORRECT': 'Corrección de transcripción',
        
        # Administración
        'ADMIN_PANEL_ACCESS': 'Acceso al panel de administración',
        'ADMIN_STATS_VIEW': 'Visualización de estadísticas',
        'ADMIN_BACKUP_CREATE': 'Creación de respaldo',
        'ADMIN_BACKUP_RESTORE': 'Restauración de respaldo',
        
        # Seguridad
        'SECURITY_VIOLATION': 'Violación de seguridad',
        'UNAUTHORIZED_ACCESS': 'Acceso no autorizado',
        'SUSPICIOUS_ACTIVITY': 'Actividad sospechosa',
        
        # Sistema
        'SYSTEM_ERROR': 'Error del sistema',
        'SYSTEM_WARNING': 'Advertencia del sistema',
        'SYSTEM_INFO': 'Información del sistema',
        
        # Exportación
        'EXPORT_CSV': 'Exportación a CSV',
        'EXPORT_PDF': 'Exportación a PDF',
        'EXPORT_EXCEL': 'Exportación a Excel'
    }
    
    @staticmethod
    def log_evento(tipo_evento, descripcion, categoria='SYSTEM', datos_adicionales=None, usuario_id=None):
        """
        Registrar un evento en el sistema de logs
        
        Args:
            tipo_evento (str): Tipo de evento (de EVENTOS)
            descripcion (str): Descripción detallada del evento
            categoria (str): Categoría del evento (de CATEGORIAS)
            datos_adicionales (dict): Datos adicionales en formato JSON
            usuario_id (int): ID del usuario (si no se proporciona, usa current_user)
        """
        try:
            # Obtener información del usuario
            if usuario_id is None and current_user.is_authenticated:
                usuario_id = current_user.id
            
            # Obtener información de la petición
            ip_address = request.remote_addr if request else None
            user_agent = request.headers.get('User-Agent') if request else None
            
            # Crear el log
            log = LogEvento(
                tipo_evento=tipo_evento,
                descripcion=descripcion,
                usuario_id=usuario_id,
                ip_address=ip_address,
                user_agent=user_agent,
                datos_adicionales=datos_adicionales or {}
            )
            
            db.session.add(log)
            db.session.commit()
            
            # Log en consola para desarrollo
            if current_app.debug:
                print(f"📝 LOG [{categoria}] {tipo_evento}: {descripcion}")
                
        except Exception as e:
            print(f"❌ Error al registrar log: {e}")
            db.session.rollback()
    
    @staticmethod
    def log_login_success(username, ip_address=None):
        """Log de inicio de sesión exitoso"""
        SistemaLogging.log_evento(
            'LOGIN_SUCCESS',
            f'Usuario {username} inició sesión correctamente',
            'AUTH',
            {'username': username, 'ip_address': ip_address}
        )
    
    @staticmethod
    def log_login_failed(username, ip_address=None, reason='Credenciales incorrectas'):
        """Log de intento de inicio de sesión fallido"""
        SistemaLogging.log_evento(
            'LOGIN_FAILED',
            f'Intento de inicio de sesión fallido para {username}: {reason}',
            'AUTH',
            {'username': username, 'ip_address': ip_address, 'reason': reason}
        )
    
    @staticmethod
    def log_logout(username):
        """Log de cierre de sesión"""
        SistemaLogging.log_evento(
            'LOGOUT',
            f'Usuario {username} cerró sesión',
            'AUTH',
            {'username': username}
        )
    
    @staticmethod
    def log_user_create(username, created_user_data):
        """Log de creación de usuario"""
        SistemaLogging.log_evento(
            'USER_CREATE',
            f'Usuario {username} creó un nuevo usuario: {created_user_data.get("username", "N/A")}',
            'USER',
            {'created_user': created_user_data}
        )
    
    @staticmethod
    def log_user_update(username, user_id, changes):
        """Log de actualización de usuario"""
        SistemaLogging.log_evento(
            'USER_UPDATE',
            f'Usuario {username} actualizó el usuario ID {user_id}',
            'USER',
            {'user_id': user_id, 'changes': changes}
        )
    
    @staticmethod
    def log_user_delete(username, deleted_user_data):
        """Log de eliminación de usuario"""
        SistemaLogging.log_evento(
            'USER_DELETE',
            f'Usuario {username} eliminó el usuario: {deleted_user_data.get("username", "N/A")}',
            'USER',
            {'deleted_user': deleted_user_data}
        )
    
    @staticmethod
    def log_case_create(username, caso_data):
        """Log de creación de caso"""
        SistemaLogging.log_evento(
            'CASE_CREATE',
            f'Usuario {username} creó el caso: {caso_data.get("expediente", "N/A")}',
            'CASE',
            {'caso': caso_data}
        )
    
    @staticmethod
    def log_case_update(username, caso_id, changes):
        """Log de actualización de caso"""
        SistemaLogging.log_evento(
            'CASE_UPDATE',
            f'Usuario {username} actualizó el caso ID {caso_id}',
            'CASE',
            {'caso_id': caso_id, 'changes': changes}
        )
    
    @staticmethod
    def log_case_delete(username, caso_data):
        """Log de eliminación de caso"""
        SistemaLogging.log_evento(
            'CASE_DELETE',
            f'Usuario {username} eliminó el caso: {caso_data.get("expediente", "N/A")}',
            'CASE',
            {'caso': caso_data}
        )
    
    @staticmethod
    def log_file_upload(username, archivo_data, caso_id):
        """Log de carga de archivo"""
        SistemaLogging.log_evento(
            'FILE_UPLOAD',
            f'Usuario {username} cargó archivo: {archivo_data.get("nombre_original", "N/A")} al caso ID {caso_id}',
            'FILE',
            {'archivo': archivo_data, 'caso_id': caso_id}
        )
    
    @staticmethod
    def log_file_download(username, archivo_data, caso_id):
        """Log de descarga de archivo"""
        SistemaLogging.log_evento(
            'FILE_DOWNLOAD',
            f'Usuario {username} descargó archivo: {archivo_data.get("nombre_original", "N/A")} del caso ID {caso_id}',
            'FILE',
            {'archivo': archivo_data, 'caso_id': caso_id}
        )
    
    @staticmethod
    def log_transcript_start(username, archivo_data, caso_id):
        """Log de inicio de transcripción"""
        SistemaLogging.log_evento(
            'TRANSCRIPT_START',
            f'Usuario {username} inició transcripción del archivo: {archivo_data.get("nombre_original", "N/A")} del caso ID {caso_id}',
            'TRANSCRIPT',
            {'archivo': archivo_data, 'caso_id': caso_id}
        )
    
    @staticmethod
    def log_transcript_complete(username, archivo_data, caso_id, confianza=None):
        """Log de transcripción completada"""
        SistemaLogging.log_evento(
            'TRANSCRIPT_COMPLETE',
            f'Usuario {username} completó transcripción del archivo: {archivo_data.get("nombre_original", "N/A")} del caso ID {caso_id}',
            'TRANSCRIPT',
            {'archivo': archivo_data, 'caso_id': caso_id, 'confianza': confianza}
        )
    
    @staticmethod
    def log_admin_action(username, action, details):
        """Log de acción administrativa"""
        SistemaLogging.log_evento(
            'ADMIN_PANEL_ACCESS',
            f'Usuario {username} realizó acción administrativa: {action}',
            'ADMIN',
            {'action': action, 'details': details}
        )
    
    @staticmethod
    def log_security_violation(username, violation_type, details):
        """Log de violación de seguridad"""
        SistemaLogging.log_evento(
            'SECURITY_VIOLATION',
            f'Violación de seguridad detectada: {violation_type} - Usuario: {username}',
            'SECURITY',
            {'violation_type': violation_type, 'details': details}
        )
    
    @staticmethod
    def log_export(username, export_type, details):
        """Log de exportación"""
        SistemaLogging.log_evento(
            'EXPORT_CSV' if export_type == 'csv' else 'EXPORT_PDF' if export_type == 'pdf' else 'EXPORT_EXCEL',
            f'Usuario {username} exportó datos en formato {export_type.upper()}',
            'EXPORT',
            {'export_type': export_type, 'details': details}
        )

# Función de conveniencia para uso en las rutas
def log_evento(tipo_evento, descripcion, categoria='SYSTEM', datos_adicionales=None, usuario_id=None):
    """Función de conveniencia para registrar eventos"""
    SistemaLogging.log_evento(tipo_evento, descripcion, categoria, datos_adicionales, usuario_id)
