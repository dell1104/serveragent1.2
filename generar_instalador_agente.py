#!/usr/bin/env python3
"""
Generador de Instaladores de Agente Forense
Crea instaladores EXE/MSI personalizados con usuario y token
"""

import os
import sys
import json
import uuid
import tempfile
import shutil
import subprocess
from pathlib import Path

def verificar_python():
    """Verifica si Python está instalado"""
    try:
        version = sys.version_info
        if version.major >= 3 and version.minor >= 7:
            return True, f"Python {version.major}.{version.minor}.{version.micro}"
        else:
            return False, f"Python {version.major}.{version.minor}.{version.micro} (se requiere 3.7+)"
    except Exception as e:
        return False, f"Error verificando Python: {e}"

def instalar_dependencias():
    """Instala las dependencias necesarias"""
    dependencias = [
        'flask==2.3.3',
        'flask-cors==4.0.0',
        'psutil==5.9.6',
        'wmi==1.5.1',
        'requests==2.31.0',
        'pyinstaller==6.1.0'
    ]
    
    print("Instalando dependencias...")
    for dep in dependencias:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', dep], 
                         check=True, capture_output=True)
            print(f"✓ {dep}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Error instalando {dep}: {e}")
            return False
    return True

def crear_instalador_bat(server_url, token, user_id):
    """Crea un instalador BAT que simula interfaz gráfica"""
    
    # Crear directorio temporal
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Creando instalador en: {temp_dir}")
        
        # Crear estructura de directorios
        install_dir = os.path.join(temp_dir, 'instalador')
        os.makedirs(install_dir, exist_ok=True)
        
        # Copiar agente
        shutil.copy('agente_windows_parametrizado.py', install_dir)
        
        # Crear script de instalación
        install_script = f'''@echo off
setlocal enabledelayedexpansion

:: Verificar permisos de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Este instalador requiere permisos de administrador
    echo Ejecuta como administrador y vuelve a intentar
    pause
    exit /b 1
)

echo ========================================
echo    INSTALADOR AGENTE FORENSE
echo    Usuario: {user_id}
echo ========================================
echo.

:: Crear directorio de instalacion
set INSTALL_DIR=C:\\Program Files\\SistemaForenseAgente
echo [INFO] Creando directorio: %INSTALL_DIR%
mkdir "%INSTALL_DIR%" 2>nul

:: Copiar archivos
echo [INFO] Copiando archivos del agente...
copy "agente_windows_parametrizado.py" "%INSTALL_DIR%\\"

:: Verificar Python
echo [INFO] Verificando Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python no esta instalado
    echo Por favor instala Python 3.7+ desde https://python.org
    pause
    exit /b 1
)

:: Instalar dependencias
echo [INFO] Instalando dependencias Python...
cd /d "%INSTALL_DIR%"
pip install flask==2.3.3 flask-cors==4.0.0 psutil==5.9.6 wmi==1.5.1 requests==2.31.0

:: Crear script de inicio
echo [INFO] Creando script de inicio...
(
echo @echo off
echo cd /d "%INSTALL_DIR%"
echo python agente_windows_parametrizado.py --server_url "{server_url}" --token "{token}"
echo pause
) > "%INSTALL_DIR%\\iniciar_agente.bat"

:: Crear acceso directo en el escritorio
echo [INFO] Creando acceso directo...
set DESKTOP=%USERPROFILE%\\Desktop
(
echo [InternetShortcut]
echo URL=http://127.0.0.1:5001
echo IconFile=%INSTALL_DIR%\\iniciar_agente.bat
echo IconIndex=0
) > "%DESKTOP%\\Agente Forense.url"

:: Crear entrada en el menu inicio
echo [INFO] Creando entrada en el menu inicio...
set START_MENU=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs
mkdir "%START_MENU%\\Sistema Forense" 2>nul
copy "%INSTALL_DIR%\\iniciar_agente.bat" "%START_MENU%\\Sistema Forense\\"

:: Configurar firewall
echo [INFO] Configurando firewall...
netsh advfirewall firewall add rule name="Agente Forense" dir=in action=allow protocol=TCP localport=5001

echo.
echo ========================================
echo    INSTALACION COMPLETADA
echo ========================================
echo.
echo El agente forense ha sido instalado en:
echo %INSTALL_DIR%
echo.
echo Para iniciar el agente:
echo 1. Ejecuta "iniciar_agente.bat" desde el escritorio
echo 2. O ve a Menu Inicio ^> Sistema Forense
echo.
echo El agente estara disponible en: http://127.0.0.1:5001
echo.
echo ¿Deseas iniciar el agente ahora? (S/N)
set /p choice=
if /i "%choice%"=="S" (
    start "" "%INSTALL_DIR%\\iniciar_agente.bat"
)
pause
'''
        
        # Guardar script de instalación
        install_path = os.path.join(install_dir, 'Instalar_Agente_Forense.bat')
        with open(install_path, 'w', encoding='utf-8') as f:
            f.write(install_script)
        
        # Crear ZIP del instalador
        zip_path = f'Instalador_Agente_Forense_{user_id}.zip'
        shutil.make_archive(zip_path.replace('.zip', ''), 'zip', install_dir)
        
        print(f"✓ Instalador creado: {zip_path}")
        return zip_path

def crear_instalador_exe(server_url, token, user_id):
    """Crea un instalador EXE usando PyInstaller"""
    
    # Crear directorio temporal
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Creando instalador EXE en: {temp_dir}")
        
        # Crear estructura de directorios
        install_dir = os.path.join(temp_dir, 'instalador')
        os.makedirs(install_dir, exist_ok=True)
        
        # Copiar agente
        shutil.copy('agente_windows_parametrizado.py', install_dir)
        
        # Crear script de instalación Python
        install_script = f'''#!/usr/bin/env python3
"""
Instalador de Agente Forense
"""

import os
import sys
import subprocess
import ctypes
import tempfile
import shutil
from pathlib import Path

def is_admin():
    """Verifica si se ejecuta como administrador"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def mostrar_error(mensaje):
    """Muestra un popup de error"""
    ctypes.windll.user32.MessageBoxW(0, mensaje, "Error - Instalador", 0x10 | 0x0)

def mostrar_info(mensaje):
    """Muestra un popup de información"""
    ctypes.windll.user32.MessageBoxW(0, mensaje, "Instalador", 0x40 | 0x0)

def verificar_python():
    """Verifica si Python está instalado"""
    try:
        result = subprocess.run([sys.executable, '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, "Python no encontrado"
    except Exception as e:
        return False, str(e)

def instalar_dependencias():
    """Instala las dependencias necesarias"""
    dependencias = [
        'flask==2.3.3',
        'flask-cors==4.0.0',
        'psutil==5.9.6',
        'wmi==1.5.1',
        'requests==2.31.0'
    ]
    
    print("Instalando dependencias...")
    for dep in dependencias:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', dep], 
                         check=True, capture_output=True)
            print(f"✓ {dep}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Error instalando {dep}: {e}")
            return False
    return True

def crear_acceso_directo():
    """Crea acceso directo en el escritorio"""
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        path = os.path.join(desktop, "Agente Forense.lnk")
        target = r"C:\\Program Files\\SistemaForenseAgente\\iniciar_agente.bat"
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = r"C:\\Program Files\\SistemaForenseAgente"
        shortcut.IconLocation = target
        shortcut.save()
        
        return True
    except Exception as e:
        print(f"Error creando acceso directo: {e}")
        return False

def main():
    print("=== INSTALADOR AGENTE FORENSE ===")
    print(f"Usuario: {user_id}")
    print(f"Servidor: {server_url}")
    print()
    
    # Verificar permisos de administrador
    if not is_admin():
        mostrar_error("Este instalador requiere permisos de administrador.\\nEjecuta como administrador y vuelve a intentar.")
        sys.exit(1)
    
    # Verificar Python
    python_ok, python_version = verificar_python()
    if not python_ok:
        mostrar_error(f"Python no está instalado o no es compatible.\\nSe requiere Python 3.7+\\n\\nError: {python_version}")
        sys.exit(1)
    
    print(f"✓ Python encontrado: {python_version}")
    
    # Crear directorio de instalación
    install_dir = r"C:\\Program Files\\SistemaForenseAgente"
    try:
        os.makedirs(install_dir, exist_ok=True)
        print(f"✓ Directorio creado: {install_dir}")
    except Exception as e:
        mostrar_error(f"No se pudo crear el directorio de instalación: {e}")
        sys.exit(1)
    
    # Copiar archivos
    try:
        shutil.copy('agente_windows_parametrizado.py', install_dir)
        print("✓ Archivos copiados")
    except Exception as e:
        mostrar_error(f"Error copiando archivos: {e}")
        sys.exit(1)
    
    # Instalar dependencias
    if not instalar_dependencias():
        mostrar_error("Error instalando dependencias. Verifica tu conexión a internet.")
        sys.exit(1)
    
    # Crear script de inicio
    start_script = f'''@echo off
cd /d "{install_dir}"
python agente_windows_parametrizado.py --server_url "{server_url}" --token "{token}"
pause
'''
    
    start_path = os.path.join(install_dir, 'iniciar_agente.bat')
    with open(start_path, 'w', encoding='utf-8') as f:
        f.write(start_script)
    
    print("✓ Script de inicio creado")
    
    # Crear acceso directo
    if crear_acceso_directo():
        print("✓ Acceso directo creado en el escritorio")
    else:
        print("⚠ No se pudo crear acceso directo")
    
    # Configurar firewall
    try:
        subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule', 
                       'name=Agente Forense', 'dir=in', 'action=allow', 
                       'protocol=TCP', 'localport=5001'], 
                      check=True, capture_output=True)
        print("✓ Firewall configurado")
    except subprocess.CalledProcessError:
        print("⚠ No se pudo configurar firewall")
    
    # Mostrar mensaje de éxito
    mostrar_info(f"Instalación completada exitosamente!\\n\\nEl agente ha sido instalado en:\\n{install_dir}\\n\\nPara iniciar el agente, ejecuta el acceso directo en el escritorio.")
    
    # Preguntar si iniciar ahora
    choice = input("¿Deseas iniciar el agente ahora? (S/N): ")
    if choice.upper() == 'S':
        try:
            subprocess.Popen([start_path], shell=True)
            print("✓ Agente iniciado")
        except Exception as e:
            print(f"Error iniciando agente: {e}")

if __name__ == "__main__":
    main()
'''
        
        # Guardar script de instalación
        install_path = os.path.join(install_dir, 'instalador.py')
        with open(install_path, 'w', encoding='utf-8') as f:
            f.write(install_script)
        
        # Compilar con PyInstaller
        try:
            cmd = [
                sys.executable, '-m', 'PyInstaller',
                '--onefile',
                '--windowed',
                '--name', f'Instalador_Agente_Forense_{user_id}',
                '--distpath', temp_dir,
                install_path
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✓ Instalador EXE compilado")
            
            # Buscar el archivo generado
            exe_files = list(Path(temp_dir).glob('*.exe'))
            if exe_files:
                exe_path = exe_files[0]
                final_path = f'Instalador_Agente_Forense_{user_id}.exe'
                shutil.copy(exe_path, final_path)
                print(f"✓ Instalador EXE creado: {final_path}")
                return final_path
            else:
                print("✗ No se encontró el archivo EXE generado")
                return None
                
        except subprocess.CalledProcessError as e:
            print(f"✗ Error compilando instalador: {e}")
            return None

def main():
    print("=== GENERADOR DE INSTALADORES AGENTE FORENSE ===")
    print()
    
    # Verificar Python
    python_ok, python_version = verificar_python()
    if not python_ok:
        print(f"✗ {python_version}")
        sys.exit(1)
    
    print(f"✓ {python_version}")
    
    # Instalar dependencias
    if not instalar_dependencias():
        print("✗ Error instalando dependencias")
        sys.exit(1)
    
    # Obtener parámetros
    print()
    server_url = input("URL del servidor (ej: http://192.168.1.93:5000): ").strip()
    if not server_url:
        server_url = "http://192.168.1.93:5000"
    
    token = input("Token de registro: ").strip()
    if not token:
        token = str(uuid.uuid4())
        print(f"Token generado automáticamente: {token}")
    
    user_id = input("ID del usuario: ").strip()
    if not user_id:
        user_id = f"USER_{uuid.uuid4().hex[:8]}"
        print(f"ID de usuario generado: {user_id}")
    
    print()
    print("=== GENERANDO INSTALADORES ===")
    
    # Crear instalador BAT
    print("1. Creando instalador BAT...")
    bat_path = crear_instalador_bat(server_url, token, user_id)
    if bat_path:
        print(f"✓ Instalador BAT creado: {bat_path}")
    else:
        print("✗ Error creando instalador BAT")
    
    # Crear instalador EXE
    print("2. Creando instalador EXE...")
    exe_path = crear_instalador_exe(server_url, token, user_id)
    if exe_path:
        print(f"✓ Instalador EXE creado: {exe_path}")
    else:
        print("✗ Error creando instalador EXE")
    
    print()
    print("=== INSTALADORES GENERADOS ===")
    if bat_path:
        print(f"• Instalador BAT: {bat_path}")
    if exe_path:
        print(f"• Instalador EXE: {exe_path}")
    
    print()
    print("¡Instaladores generados exitosamente!")

if __name__ == "__main__":
    main()
