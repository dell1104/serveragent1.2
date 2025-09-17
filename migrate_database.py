#!/usr/bin/env python3
"""
Script de migración para actualizar la base de datos
Agrega los nuevos campos para la funcionalidad de agentes
"""

import os
import sys
from datetime import datetime

# Agregar el directorio actual al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Usuario

def migrate_database():
    """Migrar la base de datos agregando nuevos campos"""
    with app.app_context():
        try:
            print("=== INICIANDO MIGRACIÓN DE BASE DE DATOS ===")
            
            # Verificar si ya existen las nuevas columnas
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('usuarios')]
            
            new_columns = [
                'es_agente', 'agente_id', 'api_key', 'ubicacion_agente',
                'sistema_operativo', 'capacidades_forenses', 'ip_agente',
                'puerto_agente', 'estado_agente', 'ultima_conexion',
                'version_agente', 'max_operaciones_concurrentes'
            ]
            
            missing_columns = [col for col in new_columns if col not in existing_columns]
            
            if not missing_columns:
                print("✓ Todas las columnas ya existen. No se requiere migración.")
                return True
            
            print(f"Columnas faltantes: {missing_columns}")
            
            # Crear las nuevas tablas y columnas
            print("Creando nuevas tablas y columnas...")
            db.create_all()
            
            # Verificar que las columnas se crearon correctamente
            inspector = db.inspect(db.engine)
            updated_columns = [col['name'] for col in inspector.get_columns('usuarios')]
            
            for col in new_columns:
                if col in updated_columns:
                    print(f"✓ Columna '{col}' creada correctamente")
                else:
                    print(f"✗ Error: Columna '{col}' no se pudo crear")
                    return False
            
            # Crear un usuario administrador por defecto si no existe
            admin_user = Usuario.query.filter_by(username='admin').first()
            if not admin_user:
                print("Creando usuario administrador por defecto...")
                admin_user = Usuario(
                    username='admin',
                    email='admin@sistema-forense.com',
                    nombre_completo='Administrador del Sistema',
                    rol='admin'
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                print("✓ Usuario administrador creado (username: admin, password: admin123)")
            
            print("=== MIGRACIÓN COMPLETADA EXITOSAMENTE ===")
            return True
            
        except Exception as e:
            print(f"✗ Error durante la migración: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = migrate_database()
    sys.exit(0 if success else 1)
