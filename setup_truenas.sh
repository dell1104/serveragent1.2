#!/bin/bash

# Script de configuración para TrueNAS + Portainer
# Sistema Forense con nueva arquitectura

echo "=== CONFIGURACIÓN SISTEMA FORENSE EN TRUENAS ==="
echo "Fecha: $(date)"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "forensic_agent.py" ]; then
    echo "❌ Error: forensic_agent.py no encontrado"
    echo "Por favor ejecuta este script desde el directorio del proyecto"
    exit 1
fi

echo "✅ Archivos del proyecto encontrados"

# Crear directorios necesarios en TrueNAS
echo "📁 Creando directorios en TrueNAS..."
mkdir -p /mnt/Respaldo/sistema-forense/{forensic_data,logs,temp,agentes_data,casos_data,static/uploads,json}

# Verificar permisos
echo "🔐 Configurando permisos..."
chmod -R 755 /mnt/Respaldo/sistema-forense/
chown -R 1000:1000 /mnt/Respaldo/sistema-forense/

# Crear archivo de configuración de Nginx
echo "🌐 Creando configuración de Nginx..."
cat > nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:5000;
    }
    
    upstream forensic_agent {
        server forensic_agent:5001;
    }
    
    server {
        listen 80;
        server_name localhost;
        
        # Aplicación principal
        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # API del agente forense
        location /api/forensic/ {
            rewrite ^/api/forensic/(.*) /$1 break;
            proxy_pass http://forensic_agent;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Archivos estáticos
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
EOF

echo "✅ Configuración de Nginx creada"

# Crear script de inicio
echo "🚀 Creando script de inicio..."
cat > start_forensic_truenas.sh << 'EOF'
#!/bin/bash

echo "=== INICIANDO SISTEMA FORENSE EN TRUENAS ==="

# Verificar que Portainer esté ejecutándose
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker no está ejecutándose"
    exit 1
fi

echo "✅ Docker está ejecutándose"

# Crear red si no existe
docker network create forense_network 2>/dev/null || echo "Red ya existe"

# Iniciar servicios
echo "🚀 Iniciando servicios..."
docker-compose -f portainer-stack.yml up -d

if [ $? -eq 0 ]; then
    echo "✅ Servicios iniciados correctamente"
    echo ""
    echo "=== SISTEMA FORENSE INICIADO ==="
    echo "🌐 Aplicación principal: http://[IP_TRUENAS]:8080"
    echo "🔧 Agente forense: http://[IP_TRUENAS]:5001"
    echo "📊 Base de datos: [IP_TRUENAS]:5432"
    echo "🔄 Redis: [IP_TRUENAS]:6379"
    echo ""
    echo "Para ver los logs: docker-compose -f portainer-stack.yml logs -f"
    echo "Para detener: docker-compose -f portainer-stack.yml down"
else
    echo "❌ Error iniciando servicios"
    exit 1
fi
EOF

chmod +x start_forensic_truenas.sh

echo "✅ Script de inicio creado"

# Crear archivo de instrucciones
echo "📋 Creando instrucciones..."
cat > INSTRUCCIONES_TRUENAS.md << 'EOF'
# Sistema Forense en TrueNAS + Portainer

## Configuración en Portainer

### 1. Crear Stack
1. Acceder a Portainer
2. Ir a "Stacks" > "Add stack"
3. Nombre: "sistema-forense"
4. Copiar el contenido de `portainer-stack.yml`
5. Hacer clic en "Deploy the stack"

### 2. Configurar Volúmenes
Asegúrate de que los volúmenes estén mapeados correctamente:
- `/mnt/Respaldo/sistema-forense` → Directorio en TrueNAS
- `postgres_data` → Volumen Docker
- `redis_data` → Volumen Docker

### 3. Configurar Red
- Nombre: `forense_network`
- Driver: `bridge`

### 4. Configurar Puertos
- `8080:80` → Nginx (Aplicación principal)
- `8443:443` → Nginx (HTTPS)
- `5432:5432` → PostgreSQL
- `6379:6379` → Redis

## Acceso al Sistema

### Aplicación Principal
- URL: `http://[IP_TRUENAS]:8080`
- Usuario admin: `admin`
- Contraseña: `admin123`

### Agente Forense
- URL: `http://[IP_TRUENAS]:5001`
- API: `http://[IP_TRUENAS]:8080/api/forensic/`

## Gestión de Agentes

### Convertir Usuario en Agente
1. Iniciar sesión como administrador
2. Ir al panel de administración
3. Seleccionar un usuario
4. Usar la función "Convertir a Agente"
5. Configurar parámetros del agente

### Configuración del Agente
- IP: IP de la máquina donde se ejecuta el agente
- Puerto: 5001 (por defecto)
- Ubicación: Descripción física del agente
- Sistema operativo: Windows/Linux/Mac
- Capacidades: DD, E01, AFF4
- Máximo de operaciones: 1-5

## Monitoreo

### Ver Logs
```bash
# Todos los servicios
docker-compose -f portainer-stack.yml logs -f

# Servicio específico
docker-compose -f portainer-stack.yml logs -f forensic_agent
```

### Estado de Servicios
```bash
docker-compose -f portainer-stack.yml ps
```

### Reiniciar Servicios
```bash
docker-compose -f portainer-stack.yml restart
```

## Solución de Problemas

### Agente No Responde
1. Verificar que el contenedor esté ejecutándose
2. Comprobar logs del agente
3. Verificar conectividad de red
4. Comprobar permisos de acceso a dispositivos

### Error de Base de Datos
1. Verificar que PostgreSQL esté ejecutándose
2. Comprobar logs de la base de datos
3. Verificar que el volumen esté montado correctamente

### Error de Permisos
1. Verificar que el contenedor tenga privilegios
2. Comprobar permisos de los directorios
3. Verificar configuración de TrueNAS

## Backup y Restauración

### Backup de Base de Datos
```bash
docker-compose -f portainer-stack.yml exec db pg_dump -U forensic sistema_forense > backup.sql
```

### Restaurar Base de Datos
```bash
docker-compose -f portainer-stack.yml exec -T db psql -U forensic sistema_forense < backup.sql
```

### Backup de Archivos
```bash
tar -czf forensic_data_backup.tar.gz /mnt/Respaldo/sistema-forense/forensic_data/
```

## Actualización del Sistema

### Actualizar Código
1. Detener el stack
2. Actualizar archivos del proyecto
3. Reiniciar el stack

### Actualizar Base de Datos
```bash
docker-compose -f portainer-stack.yml exec app python migrate_database.py
```
EOF

echo "✅ Instrucciones creadas"

echo ""
echo "=== CONFIGURACIÓN COMPLETADA ==="
echo "📁 Directorios creados en /mnt/Respaldo/sistema-forense/"
echo "📋 Archivos de configuración creados:"
echo "   - portainer-stack.yml"
echo "   - nginx.conf"
echo "   - start_forensic_truenas.sh"
echo "   - INSTRUCCIONES_TRUENAS.md"
echo ""
echo "🚀 Próximos pasos:"
echo "1. Revisar INSTRUCCIONES_TRUENAS.md"
echo "2. Crear el stack en Portainer"
echo "3. Configurar los volúmenes y redes"
echo "4. Desplegar el stack"
echo ""
echo "Para iniciar el sistema:"
echo "   ./start_forensic_truenas.sh"
