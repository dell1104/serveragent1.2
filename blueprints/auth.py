# blueprints/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
import bcrypt
import datetime
from models import db, Usuario
from utils_package.logging_system import SistemaLogging, log_evento

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Por favor completa todos los campos', 'error')
            return render_template('login_sidebar.html')
        
        # Buscar usuario
        usuario = Usuario.query.filter_by(username=username, activo=True).first()
        
        if usuario and usuario.check_password(password):
            login_user(usuario)
            usuario.ultimo_acceso = datetime.datetime.utcnow()
            db.session.commit()
            
            # Log del evento
            SistemaLogging.log_login_success(username, request.remote_addr)
            
            flash(f'¡Bienvenido, {usuario.nombre_completo}!', 'success')
            return redirect(url_for('index'))
        else:
            # Log del intento fallido
            SistemaLogging.log_login_failed(username, request.remote_addr, 'Credenciales incorrectas')
            
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login_sidebar.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Cerrar sesión"""
    username = current_user.username
    
    # Log del evento
    SistemaLogging.log_logout(username)
    
    logout_user()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    """Página de registro de nuevos usuarios"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        nombre_completo = request.form.get('nombre_completo')
        password = request.form.get('password')
        confirmar_password = request.form.get('confirmar_password')
        
        # Validaciones
        if not all([username, email, nombre_completo, password, confirmar_password]):
            flash('Por favor completa todos los campos', 'error')
            return render_template('registro_sidebar.html')
        
        if password != confirmar_password:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('registro_sidebar.html')
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'error')
            return render_template('registro_sidebar.html')
        
        # Verificar si el usuario ya existe
        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya está en uso', 'error')
            return render_template('registro_sidebar.html')
        
        if Usuario.query.filter_by(email=email).first():
            flash('El email ya está registrado', 'error')
            return render_template('registro_sidebar.html')
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            username=username,
            email=email,
            nombre_completo=nombre_completo,
            rol='usuario'
        )
        nuevo_usuario.set_password(password)
        
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            # Log del evento
            log_evento(
                'REGISTRO_USUARIO',
                f'Nuevo usuario registrado: {username}',
                nuevo_usuario.id,
                request.remote_addr,
                request.headers.get('User-Agent')
            )
            
            flash('Usuario registrado correctamente. Puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error al registrar el usuario. Inténtalo de nuevo.', 'error')
            print(f"Error en registro: {e}")
    
    return render_template('registro_sidebar.html')

@auth_bp.route('/perfil')
@login_required
def perfil():
    """Página de perfil del usuario"""
    return render_template('perfil.html', usuario=current_user)
