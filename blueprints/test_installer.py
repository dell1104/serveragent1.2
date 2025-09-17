# test_installer.py - Endpoint de Prueba para Instaladores

from flask import Blueprint, jsonify
import os
import json

# Blueprint para pruebas
test_installer_bp = Blueprint('test_installer', __name__, url_prefix='/api/test')

@test_installer_bp.route('/installers', methods=['GET'])
def test_installers():
    """Endpoint de prueba para instaladores"""
    try:
        # Configuración de prueba
        installers = [
            {
                "os": "windows",
                "arch": "x64",
                "name": "Windows 64-bit",
                "filename": "ForensicAgent-Windows-Installer.exe",
                "type": "exe",
                "size": "0",
                "description": "Instalador ejecutable para Windows 10/11 (64-bit)",
                "available": True
            },
            {
                "os": "windows",
                "arch": "x64",
                "name": "Windows 64-bit MSI",
                "filename": "ForensicAgent-Windows-Installer.msi",
                "type": "msi",
                "size": "0",
                "description": "Instalador MSI para Windows 10/11 (64-bit)",
                "available": True
            }
        ]
        
        return jsonify({
            'status': 'success',
            'installers': installers,
            'count': len(installers),
            'message': 'Endpoint de prueba funcionando'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@test_installer_bp.route('/download/<filename>', methods=['GET'])
def test_download(filename):
    """Endpoint de prueba para descarga"""
    try:
        # Verificar que el archivo existe
        if filename == "ForensicAgent-Windows-Installer.exe":
            return jsonify({
                'status': 'success',
                'filename': filename,
                'message': 'Archivo de prueba disponible',
                'download_url': f'/api/test/download/{filename}'
            })
        elif filename == "ForensicAgent-Windows-Installer.msi":
            return jsonify({
                'status': 'success',
                'filename': filename,
                'message': 'Archivo de prueba disponible',
                'download_url': f'/api/test/download/{filename}'
            })
        else:
            return jsonify({'error': 'Archivo no encontrado'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


