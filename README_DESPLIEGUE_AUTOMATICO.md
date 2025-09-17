# 🚀 Sistema Forense - Despliegue Automático

## 📋 Instrucciones de Despliegue

### **PASO 1: Preparar Archivos**
```bash
chmod +x preparar_archivos_automatico.sh
./preparar_archivos_automatico.sh
```

### **PASO 2: Desplegar STACK PRINCIPAL**
```bash
docker-compose -f STACK_PRINCIPAL.yml up -d
```

### **PASO 3: Desplegar STACK FORENSE**
```bash
docker-compose -f STACK_FORENSE.yml up -d
```

## ✅ **¡LISTO!**

### **Accesos:**
- **Aplicación Web:** http://localhost:8080
- **Instaladores:** http://localhost:8080/instalar-agente
- **Admin:** http://localhost:8080/admin
- **API Forense:** http://localhost:5001/status

### **Comandos Útiles:**
```bash
# Ver logs
docker-compose -f STACK_PRINCIPAL.yml logs -f
docker-compose -f STACK_FORENSE.yml logs -f

# Ver estado
docker ps

# Detener todo
docker-compose -f STACK_PRINCIPAL.yml down
docker-compose -f STACK_FORENSE.yml down
```

## 🔧 **¿Qué Hace el Sistema?**

### **STACK_PRINCIPAL:**
- Aplicación web Flask
- Base de datos PostgreSQL
- Cache Redis
- Proxy Nginx
- **Copia automáticamente** todos los archivos del sistema

### **STACK_FORENSE:**
- Agente forense con capacidades AFF4, EWF, DD
- Herramientas forenses avanzadas
- **Copia automáticamente** `forensic_agent.py` y `utils_package`

## 🎯 **Características:**

- ✅ **Despliegue automático** sin scripts manuales
- ✅ **Copia automática** de archivos
- ✅ **Creación automática** de directorios
- ✅ **Instalación automática** de dependencias
- ✅ **Configuración automática** del sistema

## 🆘 **Solución de Problemas:**

Si algo no funciona:
1. Verifica que el directorio `/mnt/Respaldo/sistema-forense` existe
2. Ejecuta `./preparar_archivos_automatico.sh` nuevamente
3. Revisa los logs con `docker-compose logs`

---
*Sistema completamente automatizado - Solo ejecuta los comandos y funciona* 🎉
