// system_detection.js - Detector de Sistema para Instaladores Web

class SystemDetector {
    constructor() {
        this.systemInfo = null;
        this.callbacks = [];
    }

    // Detectar sistema operativo
    detectOS() {
        const userAgent = navigator.userAgent.toLowerCase();
        const platform = navigator.platform.toLowerCase();
        
        if (userAgent.includes('windows') || platform.includes('win')) {
            return 'windows';
        } else if (userAgent.includes('mac') || userAgent.includes('macos') || platform.includes('mac')) {
            return 'macos';
        } else if (userAgent.includes('linux') || userAgent.includes('x11') || platform.includes('linux')) {
            return 'linux';
        } else if (userAgent.includes('android')) {
            return 'android';
        } else if (userAgent.includes('iphone') || userAgent.includes('ipad')) {
            return 'ios';
        } else {
            return 'unknown';
        }
    }

    // Detectar arquitectura
    detectArch() {
        const userAgent = navigator.userAgent.toLowerCase();
        const platform = navigator.platform.toLowerCase();
        
        if (userAgent.includes('x64') || userAgent.includes('amd64') || platform.includes('x64')) {
            return 'x64';
        } else if (userAgent.includes('arm64') || userAgent.includes('aarch64') || platform.includes('arm64')) {
            return 'arm64';
        } else if (userAgent.includes('x86') || userAgent.includes('i386') || platform.includes('x86')) {
            return 'x86';
        } else if (userAgent.includes('arm')) {
            return 'arm';
        } else {
            return 'x64'; // Por defecto
        }
    }

    // Detectar navegador
    detectBrowser() {
        const userAgent = navigator.userAgent.toLowerCase();
        
        if (userAgent.includes('chrome') && !userAgent.includes('edg')) {
            return 'chrome';
        } else if (userAgent.includes('firefox')) {
            return 'firefox';
        } else if (userAgent.includes('safari') && !userAgent.includes('chrome')) {
            return 'safari';
        } else if (userAgent.includes('edg')) {
            return 'edge';
        } else if (userAgent.includes('opera')) {
            return 'opera';
        } else {
            return 'unknown';
        }
    }

    // Detectar capacidades del sistema
    detectCapabilities() {
        const capabilities = {
            webGL: this.checkWebGL(),
            webRTC: this.checkWebRTC(),
            webAssembly: this.checkWebAssembly(),
            localStorage: this.checkLocalStorage(),
            sessionStorage: this.checkSessionStorage(),
            indexedDB: this.checkIndexedDB(),
            serviceWorker: this.checkServiceWorker(),
            pushNotifications: this.checkPushNotifications(),
            geolocation: this.checkGeolocation(),
            camera: this.checkCamera(),
            microphone: this.checkMicrophone()
        };

        return capabilities;
    }

    // Verificar WebGL
    checkWebGL() {
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            return !!gl;
        } catch (e) {
            return false;
        }
    }

    // Verificar WebRTC
    checkWebRTC() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }

    // Verificar WebAssembly
    checkWebAssembly() {
        return typeof WebAssembly === 'object';
    }

    // Verificar LocalStorage
    checkLocalStorage() {
        try {
            const test = 'test';
            localStorage.setItem(test, test);
            localStorage.removeItem(test);
            return true;
        } catch (e) {
            return false;
        }
    }

    // Verificar SessionStorage
    checkSessionStorage() {
        try {
            const test = 'test';
            sessionStorage.setItem(test, test);
            sessionStorage.removeItem(test);
            return true;
        } catch (e) {
            return false;
        }
    }

    // Verificar IndexedDB
    checkIndexedDB() {
        return 'indexedDB' in window;
    }

    // Verificar Service Worker
    checkServiceWorker() {
        return 'serviceWorker' in navigator;
    }

    // Verificar Push Notifications
    checkPushNotifications() {
        return 'Notification' in window && 'serviceWorker' in navigator;
    }

    // Verificar Geolocation
    checkGeolocation() {
        return 'geolocation' in navigator;
    }

    // Verificar Cámara
    checkCamera() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }

    // Verificar Micrófono
    checkMicrophone() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }

    // Detectar sistema completo
    detectSystem() {
        const systemInfo = {
            os: this.detectOS(),
            arch: this.detectArch(),
            browser: this.detectBrowser(),
            capabilities: this.detectCapabilities(),
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language,
            languages: navigator.languages,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine,
            screen: {
                width: screen.width,
                height: screen.height,
                colorDepth: screen.colorDepth,
                pixelDepth: screen.pixelDepth
            },
            window: {
                width: window.innerWidth,
                height: window.innerHeight,
                devicePixelRatio: window.devicePixelRatio
            }
        };

        this.systemInfo = systemInfo;
        console.log('Sistema detectado:', systemInfo);
        
        // Notificar a los callbacks
        this.callbacks.forEach(callback => {
            try {
                callback(systemInfo);
            } catch (e) {
                console.error('Error en callback de detección:', e);
            }
        });

        return systemInfo;
    }

    // Agregar callback
    onDetect(callback) {
        this.callbacks.push(callback);
    }

    // Obtener información del sistema
    getSystemInfo() {
        return this.systemInfo;
    }

    // Verificar si es compatible con instaladores
    isCompatible() {
        if (!this.systemInfo) {
            return false;
        }

        const compatibleOS = ['windows', 'linux', 'macos'];
        return compatibleOS.includes(this.systemInfo.os);
    }

    // Obtener recomendación de instalador
    getRecommendedInstaller() {
        if (!this.systemInfo) {
            return null;
        }

        const { os, arch } = this.systemInfo;
        
        // Mapeo de recomendaciones
        const recommendations = {
            'windows': {
                'x64': { type: 'exe', priority: 1 },
                'x86': { type: 'exe', priority: 2 }
            },
            'linux': {
                'x64': { type: 'deb', priority: 1 },
                'arm64': { type: 'deb', priority: 2 }
            },
            'macos': {
                'x64': { type: 'dmg', priority: 1 },
                'arm64': { type: 'dmg', priority: 2 }
            }
        };

        const osRecs = recommendations[os];
        if (!osRecs) {
            return null;
        }

        const archRec = osRecs[arch] || osRecs['x64'];
        if (!archRec) {
            return null;
        }

        return {
            os: os,
            arch: arch,
            type: archRec.type,
            priority: archRec.priority
        };
    }
}

// Crear instancia global
window.systemDetector = new SystemDetector();

// Auto-detectar al cargar
document.addEventListener('DOMContentLoaded', function() {
    window.systemDetector.detectSystem();
});

// Exportar para uso en otros scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SystemDetector;
}