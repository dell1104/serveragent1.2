#!/bin/bash

# Instalador Agente Forense para Linux
# Uso: ./instalador_linux.sh USER_ID SERVER_URL TOKEN

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

# Verificar si se ejecuta como root
if [ "$EUID" -ne 0 ]; then
    log_error "Este instalador debe ejecutarse como root (sudo)"
    exit 1
fi

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
echo "   INSTALADOR AGENTE FORENSE LINUX"
echo "========================================"
echo
echo "Usuario: $USER_ID"
echo "Servidor: $SERVER_URL"
echo "Token: $TOKEN"
echo

# Detectar distribución
if [ -f /etc/debian_version ]; then
    DISTRO="debian"
elif [ -f /etc/redhat-release ]; then
    DISTRO="redhat"
elif [ -f /etc/arch-release ]; then
    DISTRO="arch"
else
    DISTRO="unknown"
fi

log_info "Distribución detectada: $DISTRO"

# Instalar dependencias del sistema
log_info "Instalando dependencias del sistema..."

case $DISTRO in
    "debian")
        apt-get update
        apt-get install -y python3 python3-pip python3-venv curl wget
        ;;
    "redhat")
        yum update -y
        yum install -y python3 python3-pip curl wget
        ;;
    "arch")
        pacman -Syu --noconfirm python python-pip curl wget
        ;;
    *)
        log_warning "Distribución no reconocida. Asegúrate de tener Python 3.7+ instalado"
        ;;
esac

# Verificar Python
log_info "Verificando Python..."
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 no está instalado"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
log_success "Python encontrado: $PYTHON_VERSION"

# Crear directorio de instalación
INSTALL_DIR="/opt/sistema-forense-agente"
log_info "Creando directorio: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Crear usuario del sistema para el agente
log_info "Creando usuario del sistema..."
if ! id "forense-agente" &>/dev/null; then
    useradd -r -s /bin/false -d "$INSTALL_DIR" forense-agente
fi

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
python3 agente_linux_parametrizado.py --server_url "$SERVER_URL" --token "$TOKEN"
EOF

chmod +x "$INSTALL_DIR/start_agent.sh"

# Crear servicio systemd
log_info "Creando servicio systemd..."
cat > /etc/systemd/system/forense-agente.service << EOF
[Unit]
Description=Sistema Forense Agente
After=network.target

[Service]
Type=simple
User=forense-agente
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/start_agent.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Habilitar y iniciar servicio
systemctl daemon-reload
systemctl enable forense-agente
systemctl start forense-agente

# Configurar firewall (si está disponible)
if command -v ufw &> /dev/null; then
    log_info "Configurando firewall (ufw)..."
    ufw allow 5001/tcp
elif command -v firewall-cmd &> /dev/null; then
    log_info "Configurando firewall (firewalld)..."
    firewall-cmd --permanent --add-port=5001/tcp
    firewall-cmd --reload
fi

# Crear script de control
cat > /usr/local/bin/forense-agente << EOF
#!/bin/bash
case "\$1" in
    start)
        systemctl start forense-agente
        ;;
    stop)
        systemctl stop forense-agente
        ;;
    restart)
        systemctl restart forense-agente
        ;;
    status)
        systemctl status forense-agente
        ;;
    logs)
        journalctl -u forense-agente -f
        ;;
    *)
        echo "Uso: \$0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
EOF

chmod +x /usr/local/bin/forense-agente

log_success "Instalación completada!"
echo
echo "========================================"
echo "   INSTALACION COMPLETADA"
echo "========================================"
echo
echo "El agente forense ha sido instalado en:"
echo "$INSTALL_DIR"
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
    systemctl start forense-agente
    log_success "Agente iniciado"
fi
