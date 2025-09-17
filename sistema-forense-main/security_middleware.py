# security_middleware.py - Middleware de seguridad
from flask import request, jsonify, current_app
import logging
from datetime import datetime
import re

# Configurar logging de seguridad
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

# Handler para archivo de log de seguridad
file_handler = logging.FileHandler('security.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
security_logger.addHandler(file_handler)

def detect_sql_injection(data):
    """Detecta intentos de inyección SQL"""
    sql_patterns = [
        r'union\s+select',
        r'drop\s+table',
        r'delete\s+from',
        r'insert\s+into',
        r'update\s+set',
        r'--',
        r'/\*.*\*/',
        r'xp_cmdshell',
        r'sp_executesql'
    ]
    
    data_str = str(data).lower()
    for pattern in sql_patterns:
        if re.search(pattern, data_str):
            return True
    return False

def detect_xss_attack(data):
    """Detecta intentos de XSS"""
    xss_patterns = [
        r'<script.*?>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'<iframe.*?>',
        r'<object.*?>',
        r'<embed.*?>',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*='
    ]
    
    data_str = str(data)
    for pattern in xss_patterns:
        if re.search(pattern, data_str, re.IGNORECASE):
            return True
    return False

def detect_path_traversal(data):
    """Detecta intentos de path traversal"""
    path_patterns = [
        r'\.\./',
        r'\.\.\\',
        r'%2e%2e%2f',
        r'%2e%2e%5c',
        r'\.\.%2f',
        r'\.\.%5c'
    ]
    
    data_str = str(data)
    for pattern in path_patterns:
        if re.search(pattern, data_str, re.IGNORECASE):
            return True
    return False

def log_security_event(event_type, details, severity='MEDIUM'):
    """Registra eventos de seguridad"""
    timestamp = datetime.now().isoformat()
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    log_message = f"[{timestamp}] {event_type} - IP: {ip_address} - {details} - User-Agent: {user_agent}"
    
    if severity == 'HIGH':
        security_logger.error(log_message)
    elif severity == 'MEDIUM':
        security_logger.warning(log_message)
    else:
        security_logger.info(log_message)

def validate_request_data(data):
    """Valida datos de la petición en busca de ataques"""
    if not data:
        return True, "OK"
    
    # Convertir a string para análisis
    data_str = str(data)
    
    # Detectar inyección SQL
    if detect_sql_injection(data_str):
        log_security_event('SQL_INJECTION_ATTEMPT', f'Data: {data_str[:200]}', 'HIGH')
        return False, "Datos no válidos detectados"
    
    # Detectar XSS
    if detect_xss_attack(data_str):
        log_security_event('XSS_ATTEMPT', f'Data: {data_str[:200]}', 'HIGH')
        return False, "Contenido malicioso detectado"
    
    # Detectar path traversal
    if detect_path_traversal(data_str):
        log_security_event('PATH_TRAVERSAL_ATTEMPT', f'Data: {data_str[:200]}', 'HIGH')
        return False, "Ruta no válida detectada"
    
    return True, "OK"

def security_middleware(app):
    """Middleware de seguridad para Flask"""
    
    @app.before_request
    def before_request():
        """Ejecutar antes de cada petición"""
        # Validar datos de formulario
        if request.form:
            is_valid, message = validate_request_data(dict(request.form))
            if not is_valid:
                log_security_event('INVALID_FORM_DATA', message, 'MEDIUM')
                return jsonify({'error': 'Datos no válidos'}), 400
        
        # Validar datos JSON
        if request.is_json and request.get_json():
            is_valid, message = validate_request_data(request.get_json())
            if not is_valid:
                log_security_event('INVALID_JSON_DATA', message, 'MEDIUM')
                return jsonify({'error': 'Datos no válidos'}), 400
        
        # Validar parámetros de URL
        if request.args:
            is_valid, message = validate_request_data(dict(request.args))
            if not is_valid:
                log_security_event('INVALID_URL_PARAMS', message, 'MEDIUM')
                return jsonify({'error': 'Parámetros no válidos'}), 400
    
    @app.errorhandler(429)
    def handle_rate_limit(e):
        """Manejar límites de rate limiting"""
        log_security_event('RATE_LIMIT_EXCEEDED', f'IP: {request.remote_addr}', 'MEDIUM')
        return jsonify({'error': 'Demasiadas peticiones. Intenta más tarde.'}), 429
    
    @app.errorhandler(403)
    def handle_forbidden(e):
        """Manejar acceso prohibido"""
        log_security_event('FORBIDDEN_ACCESS', f'IP: {request.remote_addr} - Path: {request.path}', 'HIGH')
        return jsonify({'error': 'Acceso prohibido'}), 403
    
    @app.errorhandler(404)
    def handle_not_found(e):
        """Manejar páginas no encontradas"""
        log_security_event('NOT_FOUND_ACCESS', f'IP: {request.remote_addr} - Path: {request.path}', 'LOW')
        return jsonify({'error': 'Página no encontrada'}), 404
