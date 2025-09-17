#!/usr/bin/env python3
"""
Script para verificar que las herramientas forenses estén disponibles
"""

import subprocess
import sys

def verificar_herramienta(comando, nombre):
    """Verifica si una herramienta está disponible"""
    try:
        result = subprocess.run([comando, '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ {nombre}: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {nombre}: Error - {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {nombre}: Timeout")
        return False
    except FileNotFoundError:
        print(f"❌ {nombre}: No encontrado")
        return False
    except Exception as e:
        print(f"❌ {nombre}: Error - {e}")
        return False

def main():
    print("=== VERIFICACIÓN DE HERRAMIENTAS FORENSES ===")
    print()
    
    herramientas = [
        ('ewfacquire', 'EWF Acquire'),
        ('affacquire', 'AFF4 Acquire'),
        ('dd', 'DD (Data Duplicator)'),
        ('ewfinfo', 'EWF Info'),
        ('affverify', 'AFF4 Verify'),
        ('python3', 'Python 3'),
        ('pip3', 'Pip 3')
    ]
    
    disponibles = 0
    total = len(herramientas)
    
    for comando, nombre in herramientas:
        if verificar_herramienta(comando, nombre):
            disponibles += 1
    
    print()
    print("=== RESUMEN ===")
    print(f"Herramientas disponibles: {disponibles}/{total}")
    
    if disponibles == total:
        print("🎉 ¡Todas las herramientas están disponibles!")
        return True
    else:
        print("⚠️  Algunas herramientas no están disponibles")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
