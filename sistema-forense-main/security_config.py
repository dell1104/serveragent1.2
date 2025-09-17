# security_config.py - Configuración de seguridad del sistema

# Configuración de validación de archivos
FILE_SECURITY_CONFIG = {
    'MAX_FILE_SIZE_MB': 100,  # Tamaño máximo de archivo en MB
    'ALLOWED_EXTENSIONS': {
        'audio': ['mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac'],
        'video': ['mp4', 'avi', 'mov', 'wmv', 'mkv', 'webm'],
        'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp'],
        'document': ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt']
    },
    'DANGEROUS_EXTENSIONS': [
        'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 'jar',
        'php', 'asp', 'jsp', 'py', 'rb', 'pl', 'sh', 'ps1'
    ]
}

# Configuración de validación de inputs
INPUT_VALIDATION_CONFIG = {
    'MAX_FIELD_LENGTHS': {
        'expediente': 50,
        'origen_solicitud': 200,
        'tipo_requerimiento': 100,
        'observaciones': 1000,
        'nombre_caso': 150
    },
    'DANGEROUS_PATTERNS': [
        r'<script.*?>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'data:text/html',
        r'<iframe.*?>',
        r'<object.*?>',
        r'<embed.*?>',
        r'<link.*?>',
        r'<meta.*?>'
    ]
}

# Configuración de rate limiting
RATE_LIMITING_CONFIG = {
    'UPLOAD_LIMITS': {
        'max_uploads_per_hour': 50,
        'max_uploads_per_day': 200
    },
    'API_LIMITS': {
        'max_requests_per_minute': 60,
        'max_requests_per_hour': 1000
    }
}

# Configuración de logging de seguridad
SECURITY_LOGGING_CONFIG = {
    'LOG_LEVELS': {
        'LOW': ['FILE_UPLOAD_SUCCESS', 'CASE_CREATED'],
        'MEDIUM': ['INVALID_INPUT', 'FILE_UPLOAD_REJECTED'],
        'HIGH': ['SECURITY_ATTACK', 'UNAUTHORIZED_ACCESS', 'SUSPICIOUS_ACTIVITY']
    },
    'RETENTION_DAYS': 90  # Días para mantener logs de seguridad
}

# Headers de seguridad para respuestas HTTP
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'self' http://192.168.1.93 http://192.168.1.93:8080 http://localhost; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net http://192.168.1.93 http://192.168.1.93:8080 http://localhost; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com http://192.168.1.93 http://192.168.1.93:8080 http://localhost; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; img-src 'self' data: http://192.168.1.93 http://192.168.1.93:8080 http://localhost; connect-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com http://192.168.1.93 http://192.168.1.93:8080 http://localhost http://localhost:5001"
}
