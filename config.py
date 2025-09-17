# config.py
import os

class Config:
    """Configuración base de la aplicación"""
    
    # Configuración de la Base de Datos
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://forensic:forensic123@localhost:5432/sistema_forense'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de Seguridad
    SECRET_KEY = 'b56b26888bfb9e1def06058c3476084011ac4b9dba5ae46cb1ddc06816ef34ca'  # ¡CAMBIA ESTA CLAVE!
    
    # Configuración de seguridad de sesiones
    SESSION_COOKIE_SECURE = False  # True en producción con HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevenir acceso via JavaScript
    SESSION_COOKIE_SAMESITE = 'Lax'  # Protección CSRF
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora
    
    # Configuración de seguridad adicional
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    
    # Configuración de Carpetas
    BASE_UPLOAD_FOLDER = "casos_data"
    
    # Configuración de AssemblyAI
    ASSEMBLYAI_API_KEY = 'ff28d2ae53964f4ba3836be4cf9f82b2'
    
    # Configuración de archivos permitidos
    ALLOWED_EXTENSIONS = {
        'audio': {'mp3', 'wav', 'm4a', 'opus', 'ogg', 'flac', 'aac'},
        'video': {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv'},
        'image': {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'},
        'document': {'pdf', 'doc', 'docx', 'txt', 'rtf'},
        'whatsapp': {'txt'}
    }
    
    # Tamaño máximo de archivo (50MB)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024

class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    
    # Configuración específica para Docker/TrueNAS
    PREFERRED_URL_SCHEME = 'http'

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False

# Configuración por defecto
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
