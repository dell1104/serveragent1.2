// system_detection.js - Detección de Sistema Operativo y Capacidades

class SystemDetector {
    constructor() {
        this.systemInfo = null;
        this.agentStatus = null;
    }

    // ==================== DETECCIÓN DE SISTEMA ====================
    
    detectSystem() {
        const userAgent = navigator.userAgent;
        const platform = navigator.platform;
        
        const systemInfo = {
            os: this.detectOS(userAgent, platform),
            arch: this.detectArchitecture(userAgent, platform),
            browser: this.detectBrowser(userAgent),
            capabilities: this.detectCapabilities(),
            timestamp: new Date().toISOString()
        };

        this.systemInfo = systemInfo;
        console.log('Sistema detectado:', systemInfo);
        return systemInfo;
    }

    detectOS(userAgent, platform) {
        // Detectar sistema operativo
        if (userAgent.includes('Windows NT 10.0')) return 'windows';
        if (userAgent.includes('Windows NT 6.3')) return 'windows';
        if (userAgent.includes('Windows NT 6.1')) return 'windows';
        if (userAgent.includes('Windows')) return 'windows';
        
        if (userAgent.includes('Mac OS X')) return 'macos';
        if (userAgent.includes('Macintosh')) return 'macos';
        
        if (userAgent.includes('Linux')) return 'linux';
        if (userAgent.includes('Ubuntu')) return 'linux';
        if (userAgent.includes('Debian')) return 'linux';
        if (userAgent.includes('CentOS')) return 'linux';
        if (userAgent.includes('Red Hat')) return 'linux';
        if (userAgent.includes('Fedora')) return 'linux';
        
        if (userAgent.includes('Android')) return 'android';
        if (userAgent.includes('iPhone') || userAgent.includes('iPad')) return 'ios';
        
        return 'unknown';
    }

    detectArchitecture(userAgent, platform) {
        // Detectar arquitectura
        if (userAgent.includes('x64') || userAgent.includes('x86_64') || userAgent.includes('AMD64')) {
            return 'x64';
        }
        if (userAgent.includes('x86') || userAgent.includes('i386') || userAgent.includes('i686')) {
            return 'x86';
        }
        if (userAgent.includes('arm64') || userAgent.includes('aarch64')) {
            return 'arm64';
        }
        if (userAgent.includes('arm')) {
            return 'arm';
        }
        
        // Detectar por platform
        if (platform.includes('Win64') || platform.includes('x64')) return 'x64';
        if (platform.includes('Win32') || platform.includes('x86')) return 'x86';
        if (platform.includes('MacIntel')) return 'x64';
        if (platform.includes('MacPPC')) return 'ppc';
        
        return 'unknown';
    }

    detectBrowser(userAgent) {
        if (userAgent.includes('Chrome')) return 'chrome';
        if (userAgent.includes('Firefox')) return 'firefox';
        if (userAgent.includes('Safari')) return 'safari';
        if (userAgent.includes('Edge')) return 'edge';
        if (userAgent.includes('Opera')) return 'opera';
        return 'unknown';
    }

    detectCapabilities() {
        return {
            // Capacidades del navegador
            webGL: this.checkWebGL(),
            webRTC: this.checkWebRTC(),
            fileAPI: this.checkFileAPI(),
            localStorage: this.checkLocalStorage(),
            indexedDB: this.checkIndexedDB(),
            
            // Capacidades del sistema
            python: false, // Se detectará en el instalador
            docker: false, // Se detectará en el instalador
            admin: false,  // Se detectará en el instalador
            
            // Capacidades forenses (se detectarán en el instalador)
            ewfacquire: false,
            smartctl: false,
            pyaff4: false
        };
    }

    checkWebGL() {
        try {
            const canvas = document.createElement('canvas');
            return !!(window.WebGLRenderingContext && canvas.getContext('webgl'));
        } catch (e) {
            return false;
        }
    }

    checkWebRTC() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }

    checkFileAPI() {
        return !!(window.File && window.FileReader && window.FileList && window.Blob);
    }

    checkLocalStorage() {
        try {
            localStorage.setItem('test', 'test');
            localStorage.removeItem('test');
            return true;
        } catch (e) {
            return false;
        }
    }

    checkIndexedDB() {
        return !!(window.indexedDB || window.mozIndexedDB || window.webkitIndexedDB || window.msIndexedDB);
    }

    // ==================== DETECCIÓN DE AGENTE ====================
    
    async checkAgentStatus() {
        try {
            // Intentar conectar con agente local
            const response = await fetch('http://localhost:5001/status', {
                method: 'GET',
                headers: {
                    'Authorization': 'Bearer forensic_agent_2024',
                    'Content-Type': 'application/json'
                },
                timeout: 3000
            });

            if (response.ok) {
                const data = await response.json();
                this.agentStatus = {
                    connected: true,
                    status: data.agent.status,
                    version: data.agent.version,
                    capabilities: data.agent.available_formats,
                    lastSeen: new Date().toISOString()
                };
                return this.agentStatus;
            }
        } catch (error) {
            console.log('Agente local no disponible:', error.message);
        }

        this.agentStatus = {
            connected: false,
            status: 'disconnected',
            version: null,
            capabilities: {},
            lastSeen: null
        };

        return this.agentStatus;
    }

    // ==================== GENERACIÓN DE INSTALADOR ====================
    
    async generateInstaller() {
        if (!this.systemInfo) {
            this.detectSystem();
        }

        try {
            const response = await fetch('/api/generate-installer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({
                    system: this.systemInfo,
                    user_id: this.getCurrentUserId()
                })
            });

            if (response.ok) {
                const blob = await response.blob();
                return blob;
            } else {
                throw new Error(`Error generando instalador: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Error generando instalador:', error);
            throw error;
        }
    }

    async downloadInstaller() {
        try {
            const blob = await this.generateInstaller();
            const url = window.URL.createObjectURL(blob);
            
            // Crear nombre de archivo basado en el sistema
            const filename = this.getInstallerFilename();
            
            // Crear enlace de descarga
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            // Limpiar URL
            window.URL.revokeObjectURL(url);
            
            return true;
        } catch (error) {
            console.error('Error descargando instalador:', error);
            return false;
        }
    }

    getInstallerFilename() {
        const { os, arch } = this.systemInfo;
        const timestamp = new Date().toISOString().split('T')[0];
        
        switch (os) {
            case 'windows':
                return `forensic_agent_windows_${arch}_${timestamp}.exe`;
            case 'linux':
                return `forensic_agent_linux_${arch}_${timestamp}.sh`;
            case 'macos':
                return `forensic_agent_macos_${arch}_${timestamp}.pkg`;
            default:
                return `forensic_agent_${os}_${arch}_${timestamp}.zip`;
        }
    }

    // ==================== UTILIDADES ====================
    
    getAuthToken() {
        // Obtener token de autenticación del localStorage o cookie
        return localStorage.getItem('auth_token') || document.cookie
            .split('; ')
            .find(row => row.startsWith('auth_token='))
            ?.split('=')[1] || '';
    }

    getCurrentUserId() {
        // Obtener ID de usuario actual
        return localStorage.getItem('user_id') || 'anonymous';
    }

    // ==================== INTERFAZ DE USUARIO ====================
    
    showSystemInfo() {
        if (!this.systemInfo) {
            this.detectSystem();
        }

        const info = `
            <div class="system-info">
                <h5>Información del Sistema</h5>
                <p><strong>SO:</strong> ${this.systemInfo.os}</p>
                <p><strong>Arquitectura:</strong> ${this.systemInfo.arch}</p>
                <p><strong>Navegador:</strong> ${this.systemInfo.browser}</p>
                <p><strong>WebGL:</strong> ${this.systemInfo.capabilities.webGL ? '✅' : '❌'}</p>
                <p><strong>File API:</strong> ${this.systemInfo.capabilities.fileAPI ? '✅' : '❌'}</p>
            </div>
        `;

        return info;
    }

    showAgentStatus() {
        if (!this.agentStatus) {
            return '<p>Verificando estado del agente...</p>';
        }

        if (this.agentStatus.connected) {
            return `
                <div class="agent-status connected">
                    <h5>✅ Agente Conectado</h5>
                    <p><strong>Estado:</strong> ${this.agentStatus.status}</p>
                    <p><strong>Versión:</strong> ${this.agentStatus.version}</p>
                    <p><strong>Formatos:</strong> ${Object.keys(this.agentStatus.capabilities).join(', ')}</p>
                </div>
            `;
        } else {
            return `
                <div class="agent-status disconnected">
                    <h5>❌ Agente No Conectado</h5>
                    <p>Descargue e instale el agente para su sistema</p>
                    <button class="btn btn-primary" onclick="systemDetector.downloadInstaller()">
                        Descargar Instalador
                    </button>
                </div>
            `;
        }
    }
}

// Instancia global
const systemDetector = new SystemDetector();

// Auto-detección al cargar la página
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Iniciando detección de sistema...');
    
    // Detectar sistema
    systemDetector.detectSystem();
    
    // Verificar agente
    await systemDetector.checkAgentStatus();
    
    // Mostrar información en la página
    const systemInfoDiv = document.getElementById('system-info');
    if (systemInfoDiv) {
        systemInfoDiv.innerHTML = systemDetector.showSystemInfo();
    }
    
    const agentStatusDiv = document.getElementById('agent-status');
    if (agentStatusDiv) {
        agentStatusDiv.innerHTML = systemDetector.showAgentStatus();
    }
});

// Exportar para uso global
window.systemDetector = systemDetector;
