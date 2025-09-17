#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurar Todo - Sistema Forense
Genera instaladores e inicia el servidor
"""

import os
import sys
import subprocess

def main():
    """Función principal"""
    print("=" * 50)
    print("  Configurar Todo - Sistema Forense")
    print("=" * 50)
    
    try:
        # Generar instaladores
        print("\n🔧 Generando instaladores...")
        result = subprocess.run([sys.executable, 'generar_instaladores.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Instaladores generados")
        else:
            print(f"❌ Error generando instaladores: {result.stderr}")
            return
        
        # Iniciar servidor
        print("\n🌐 Iniciando servidor Flask...")
        print("\nPara probar la página web:")
        print("1. Abrir navegador en: http://localhost:5000/instalar-agente")
        print("2. La página detectará automáticamente tu sistema")
        print("3. Descargará el instalador correspondiente")
        print("\nPresiona Ctrl+C para detener el servidor")
        print("-" * 50)
        
        # Iniciar servidor Flask
        subprocess.run([sys.executable, 'app.py'])
        
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor detenido")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()

