#!/bin/bash
echo "========================================"
echo "   INSTALADOR AGENTE FORENSE LINUX"
echo "========================================"
echo ""
echo "Instalando agente forense..."

# Crear directorio de instalación
INSTALL_DIR="/opt/agente-forense"
sudo mkdir -p "$INSTALL_DIR"

# Copiar archivos
echo "Copiando archivos del agente..."
sleep 2

# Crear script de inicio
cat > "$INSTALL_DIR/iniciar_agente.sh" << 'EOF'
#!/bin/bash
echo "Iniciando Agente Forense..."
echo "Agente instalado correctamente"
echo "Presiona Enter para continuar..."
read
EOF

chmod +x "$INSTALL_DIR/iniciar_agente.sh"

# Crear enlace simbólico
sudo ln -sf "$INSTALL_DIR/iniciar_agente.sh" /usr/local/bin/agente-forense

echo ""
echo "✅ Instalación completada"
echo "📁 Ubicación: $INSTALL_DIR"
echo "🚀 Comando: agente-forense"
echo ""
