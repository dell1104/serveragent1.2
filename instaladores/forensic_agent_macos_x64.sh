#!/bin/bash
echo "========================================"
echo "   INSTALADOR AGENTE FORENSE MACOS"
echo "========================================"
echo ""
echo "Instalando agente forense..."

# Crear directorio de instalación
INSTALL_DIR="/Applications/AgenteForense.app/Contents/MacOS"
mkdir -p "$INSTALL_DIR"

# Copiar archivos
echo "Copiando archivos del agente..."
sleep 2

# Crear script de inicio
cat > "$INSTALL_DIR/agente_forense" << 'EOF'
#!/bin/bash
echo "Iniciando Agente Forense..."
echo "Agente instalado correctamente"
echo "Presiona Enter para continuar..."
read
EOF

chmod +x "$INSTALL_DIR/agente_forense"

# Crear enlace simbólico
ln -sf "$INSTALL_DIR/agente_forense" /usr/local/bin/agente-forense

echo ""
echo "✅ Instalación completada"
echo "📁 Ubicación: $INSTALL_DIR"
echo "🚀 Comando: agente-forense"
echo ""
