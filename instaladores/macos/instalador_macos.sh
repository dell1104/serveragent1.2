#!/bin/bash

# Instalador Agente Forense para macOS
# Uso: ./instalador_macos.sh USER_ID SERVER_URL TOKEN

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar mensajes
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Obtener parámetros
USER_ID="$1"
SERVER_URL="$2"
TOKEN="$3"

if [ -z "$USER_ID" ] || [ -z "$SERVER_URL" ] || [ -z "$TOKEN" ]; then
    log_error "Faltan parámetros requeridos"
    echo "Uso: $0 USER_ID SERVER_URL TOKEN"
    exit 1
fi

echo "========================================"
echo "   INSTALADOR AGENTE FORENSE MACOS"
echo "========================================"
echo
echo "Usuario: $USER_ID"
echo "Servidor: $SERVER_URL"
echo "Token: $TOKEN"
echo

# Verificar si Homebrew está instalado
if ! command -v brew &> /dev/null; then
    log_info "Homebrew no está instalado. Instalando..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Agregar Homebrew al PATH
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# Verificar Python
log_info "Verificando Python..."
if ! command -v python3 &> /dev/null; then
    log_info "Instalando Python 3..."
    brew install python3
fi

PYTHON_VERSION=$(python3 --version)
log_success "Python encontrado: $PYTHON_VERSION"

# Crear directorio de instalación
INSTALL_DIR="/Applications/SistemaForenseAgente"
log_info "Creando directorio: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Crear entorno virtual
log_info "Creando entorno virtual Python..."
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias Python
log_info "Instalando dependencias Python..."
pip install --upgrade pip
pip install flask==2.3.3 flask-cors==4.0.0 psutil==5.9.6 requests==2.31.0

# Crear script de inicio
log_info "Creando script de inicio..."
cat > "$INSTALL_DIR/start_agent.sh" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python3 agente_macos_parametrizado.py --server_url "$SERVER_URL" --token "$TOKEN"
EOF

chmod +x "$INSTALL_DIR/start_agent.sh"

# Crear LaunchAgent (equivalente a systemd en macOS)
log_info "Creando LaunchAgent..."
mkdir -p ~/Library/LaunchAgents

cat > ~/Library/LaunchAgents/com.sistemaforense.agente.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sistemaforense.agente</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/start_agent.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/agent.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/agent.error.log</string>
</dict>
</plist>
EOF

# Cargar el LaunchAgent
launchctl load ~/Library/LaunchAgents/com.sistemaforense.agente.plist

# Crear aplicación en /Applications
log_info "Creando aplicación..."
mkdir -p "$INSTALL_DIR/SistemaForenseAgente.app/Contents/MacOS"
mkdir -p "$INSTALL_DIR/SistemaForenseAgente.app/Contents/Resources"

# Crear Info.plist para la aplicación
cat > "$INSTALL_DIR/SistemaForenseAgente.app/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>SistemaForenseAgente</string>
    <key>CFBundleIdentifier</key>
    <string>com.sistemaforense.agente</string>
    <key>CFBundleName</key>
    <string>Sistema Forense Agente</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
</dict>
</plist>
EOF

# Crear ejecutable de la aplicación
cat > "$INSTALL_DIR/SistemaForenseAgente.app/Contents/MacOS/SistemaForenseAgente" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python3 agente_macos_parametrizado.py --server_url "$SERVER_URL" --token "$TOKEN"
EOF

chmod +x "$INSTALL_DIR/SistemaForenseAgente.app/Contents/MacOS/SistemaForenseAgente"

# Crear script de control
cat > /usr/local/bin/forense-agente << EOF
#!/bin/bash
case "\$1" in
    start)
        launchctl load ~/Library/LaunchAgents/com.sistemaforense.agente.plist
        ;;
    stop)
        launchctl unload ~/Library/LaunchAgents/com.sistemaforense.agente.plist
        ;;
    restart)
        launchctl unload ~/Library/LaunchAgents/com.sistemaforense.agente.plist
        sleep 2
        launchctl load ~/Library/LaunchAgents/com.sistemaforense.agente.plist
        ;;
    status)
        launchctl list | grep com.sistemaforense.agente
        ;;
    logs)
        tail -f "$INSTALL_DIR/agent.log"
        ;;
    *)
        echo "Uso: \$0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
EOF

chmod +x /usr/local/bin/forense-agente

# Configurar firewall (si está habilitado)
if [ "$(defaults read /Library/Preferences/com.apple.alf globalstate 2>/dev/null || echo 0)" -gt 0 ]; then
    log_info "Configurando firewall..."
    sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add "$INSTALL_DIR/start_agent.sh"
fi

log_success "Instalación completada!"
echo
echo "========================================"
echo "   INSTALACION COMPLETADA"
echo "========================================"
echo
echo "El agente forense ha sido instalado en:"
echo "$INSTALL_DIR"
echo
echo "Aplicación creada en:"
echo "$INSTALL_DIR/SistemaForenseAgente.app"
echo
echo "Comandos disponibles:"
echo "  forense-agente start    - Iniciar agente"
echo "  forense-agente stop     - Detener agente"
echo "  forense-agente restart  - Reiniciar agente"
echo "  forense-agente status   - Ver estado"
echo "  forense-agente logs     - Ver logs"
echo
echo "El agente estará disponible en: http://localhost:5001"
echo
echo "¿Deseas iniciar el agente ahora? (s/n)"
read -r choice
if [[ "$choice" =~ ^[Ss]$ ]]; then
    launchctl load ~/Library/LaunchAgents/com.sistemaforense.agente.plist
    log_success "Agente iniciado"
fi
