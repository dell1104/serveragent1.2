#!/usr/bin/env python3
"""
Script para probar la integración entre el stack principal y el stack forense
"""

import os
import sys
import requests
import time
import json
from datetime import datetime

# Agregar el directorio actual al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_forensic_agent():
    """Probar el agente forense directamente"""
    print("=== PROBANDO AGENTE FORENSE ===")
    
    try:
        # Probar endpoint de estado
        response = requests.get('http://localhost:5001/status', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Agente forense online: {data.get('agent', {}).get('name')}")
            print(f"  - Versión: {data.get('agent', {}).get('version')}")
            print(f"  - Python: {data.get('agent', {}).get('python_version')}")
            print(f"  - Capacidades: {data.get('agent', {}).get('capabilities')}")
            return True
        else:
            print(f"✗ Error conectando al agente: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error conectando al agente: {e}")
        return False

def test_main_app():
    """Probar la aplicación principal"""
    print("\n=== PROBANDO APLICACIÓN PRINCIPAL ===")
    
    try:
        # Probar endpoint de login
        response = requests.get('http://localhost:8080/login', timeout=5)
        if response.status_code == 200:
            print("✓ Aplicación principal online")
            return True
        else:
            print(f"✗ Error conectando a la aplicación: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error conectando a la aplicación: {e}")
        return False

def test_database_connection():
    """Probar conexión a la base de datos"""
    print("\n=== PROBANDO BASE DE DATOS ===")
    
    try:
        from app import app
        from models import db, Usuario
        
        with app.app_context():
            # Contar usuarios
            user_count = Usuario.query.count()
            print(f"✓ Base de datos conectada - {user_count} usuarios")
            
            # Verificar estructura de agentes
            agentes = Usuario.query.filter_by(es_agente=True).all()
            print(f"✓ {len(agentes)} agentes registrados")
            
            return True
    except Exception as e:
        print(f"✗ Error conectando a la base de datos: {e}")
        return False

def test_agent_conversion():
    """Probar conversión de usuario a agente"""
    print("\n=== PROBANDO CONVERSIÓN DE USUARIO A AGENTE ===")
    
    try:
        from app import app
        from models import db, Usuario
        
        with app.app_context():
            # Buscar un usuario que no sea agente
            usuario = Usuario.query.filter_by(es_agente=False).first()
            if not usuario:
                print("✗ No hay usuarios disponibles para convertir")
                return False
            
            print(f"✓ Usuario encontrado: {usuario.username}")
            
            # Simular conversión a agente
            usuario.es_agente = True
            usuario.generate_agent_id()
            usuario.generate_api_key()
            usuario.ip_agente = 'localhost'
            usuario.puerto_agente = 5001
            usuario.ubicacion_agente = 'Laboratorio de Pruebas'
            usuario.sistema_operativo = 'Linux'
            usuario.set_agent_capabilities(['DD', 'E01', 'AFF4'])
            usuario.max_operaciones_concurrentes = 2
            
            db.session.commit()
            
            print(f"✓ Usuario convertido a agente: {usuario.agente_id}")
            print(f"  - API Key: {usuario.api_key[:10]}...")
            print(f"  - Capacidades: {usuario.capacidades_forenses}")
            
            return True
    except Exception as e:
        print(f"✗ Error en conversión: {e}")
        return False

def test_forensic_operation():
    """Probar operación forense completa"""
    print("\n=== PROBANDO OPERACIÓN FORENSE ===")
    
    try:
        # Probar listado de discos
        response = requests.get('http://localhost:5001/disks', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Discos disponibles: {len(data.get('disks', []))}")
            
            # Mostrar algunos discos
            for i, disk in enumerate(data.get('disks', [])[:3]):
                print(f"  - Disco {i+1}: {disk.get('device')} ({disk.get('fstype')})")
        else:
            print(f"✗ Error listando discos: {response.status_code}")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Error en operación forense: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("INICIANDO PRUEBAS DE INTEGRACIÓN")
    print("=" * 50)
    
    tests = [
        ("Base de datos", test_database_connection),
        ("Aplicación principal", test_main_app),
        ("Agente forense", test_forensic_agent),
        ("Conversión usuario-agente", test_agent_conversion),
        ("Operación forense", test_forensic_operation)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Error en {test_name}: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("RESULTADOS DE PRUEBAS:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:30} {status}")
        if result:
            passed += 1
    
    print(f"\nPruebas pasadas: {passed}/{len(results)}")
    
    if passed == len(results):
        print("🎉 ¡Todas las pruebas pasaron!")
        return True
    else:
        print("⚠️  Algunas pruebas fallaron")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
