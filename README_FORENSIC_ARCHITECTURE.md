# Sistema Forense - Nueva Arquitectura

## Resumen de Cambios

Se ha implementado una nueva arquitectura que simplifica la gestión de agentes forenses y mejora la compatibilidad con herramientas forenses.

### 1. Nuevo Stack Forense con Python 3.9

- **Dockerfile.forensic**: Contenedor especializado con Python 3.9
- **Debian Bullseye**: Base estable para herramientas forenses
- **Dependencias optimizadas**: pyaff4, pyewf, dfvfs, etc.
- **Herramientas del sistema**: ewfacquire, aff4acquire, dd

### 2. Arquitectura Usuario-Agente Unificada

- **Eliminación de separación**: Los usuarios ahora pueden ser agentes directamente
- **Modelo simplificado**: Un solo modelo `Usuario` con capacidades de agente
- **Gestión centralizada**: Administración desde el panel principal

## Estructura del Sistema

```
Sistema Forense
├── Stack Principal (Python 3.13)
│   ├── Aplicación web
│   ├── Base de datos PostgreSQL
│   ├── Redis
│   └── Nginx
├── Stack Forense (Python 3.9)
│   ├── Agente forense
│   ├── Herramientas E01/AFF4
│   └── Adquisición de discos
└── Datos compartidos
    ├── forensic_data/
    ├── logs/
    └── temp/
```

## Nuevos Campos en el Modelo Usuario

### Campos de Agente
- `es_agente`: Boolean - Indica si el usuario es un agente
- `agente_id`: String - ID único del agente
- `api_key`: String - Clave API para comunicación
- `ubicacion_agente`: String - Ubicación física del agente
- `sistema_operativo`: String - OS del agente
- `capacidades_forenses`: JSON - ['DD', 'E01', 'AFF4']
- `ip_agente`: String - IP del agente
- `puerto_agente`: Integer - Puerto del agente (default: 5001)
- `estado_agente`: String - online, offline, error
- `ultima_conexion`: DateTime - Última conexión
- `version_agente`: String - Versión del agente
- `max_operaciones_concurrentes`: Integer - Máximo de operaciones simultáneas

### Nuevo Modelo OperacionForense
- `operation_id`: String - ID único de la operación
- `caso_id`: String - ID del caso
- `dispositivo_id`: String - ID del dispositivo
- `formato_adquisicion`: String - DD, E01, AFF4
- `nombre_archivo`: String - Nombre del archivo de salida
- `estado`: String - iniciando, en_progreso, completado, error, cancelado
- `progreso`: Float - Progreso de la operación (0-100)
- `archivo_salida`: String - Ruta del archivo generado
- `tamaño_archivo`: BigInteger - Tamaño en bytes
- `hash_archivo`: String - Hash SHA256 del archivo
- `fecha_inicio`: DateTime - Fecha de inicio
- `fecha_fin`: DateTime - Fecha de finalización
- `error_mensaje`: Text - Mensaje de error si aplica
- `datos_adicionales`: JSON - Datos adicionales
- `usuario_agente_id`: ForeignKey - Referencia al usuario/agente

## Nuevos Endpoints

### Gestión de Agentes
- `GET /api/agentes` - Listar todos los agentes
- `GET /api/agentes/<agent_id>/discos` - Listar discos de un agente
- `POST /api/agentes/<agent_id>/adquirir` - Iniciar adquisición
- `GET /api/agentes/<agent_id>/operacion/<operation_id>/estado` - Estado de operación
- `POST /api/agentes/<agent_id>/operacion/<operation_id>/cancelar` - Cancelar operación

### Conversión Usuario-Agente
- `POST /api/usuarios/<user_id>/convertir-agente` - Convertir usuario en agente
- `POST /api/agentes/<agent_id>/desactivar` - Desactivar agente

## Instalación y Configuración

### 1. Preparar el Sistema
```bash
# Crear directorios necesarios
mkdir -p /mnt/Respaldo/sistema-forense/{forensic_data,logs,temp,agentes_data}
mkdir -p /mnt/Respaldo/sistema-forense/static/uploads
```

### 2. Iniciar el Sistema
```bash
# Linux/Mac
./start_forensic_system.sh

# Windows
start_forensic_system.bat
```

### 3. Verificar Instalación
```bash
# Verificar servicios
docker-compose ps

# Ver logs
docker-compose logs -f

# Probar integración
docker-compose exec app python test_integration.py
```

## Uso del Sistema

### 1. Acceso a la Aplicación
- **URL Principal**: http://localhost:8080
- **Agente Forense**: http://localhost:5001
- **Usuario Admin**: admin / admin123

### 2. Convertir Usuario en Agente
1. Iniciar sesión como administrador
2. Ir al panel de administración
3. Seleccionar un usuario
4. Usar la función "Convertir a Agente"
5. Configurar parámetros del agente:
   - IP del agente
   - Puerto (default: 5001)
   - Ubicación
   - Sistema operativo
   - Capacidades forenses
   - Máximo de operaciones concurrentes

### 3. Usar Agente para Adquisición
1. Verificar que el agente esté online
2. Seleccionar el agente en la interfaz
3. Elegir dispositivo a adquirir
4. Seleccionar formato (DD, E01, AFF4)
5. Iniciar adquisición
6. Monitorear progreso

## Ventajas de la Nueva Arquitectura

### 1. Simplificación
- **Un solo modelo**: Usuario y agente en la misma entidad
- **Gestión unificada**: Administración desde un solo lugar
- **Menos complejidad**: Eliminación de tablas redundantes

### 2. Compatibilidad Forense
- **Python 3.9**: Mejor compatibilidad con pyaff4 y E01
- **Herramientas nativas**: ewfacquire, aff4acquire, dd
- **Dependencias optimizadas**: Versiones específicas para forense

### 3. Escalabilidad
- **Múltiples agentes**: Cada usuario puede ser un agente
- **Distribución**: Agentes en diferentes ubicaciones
- **Concurrencia**: Control de operaciones simultáneas

### 4. Seguridad
- **API Keys**: Autenticación segura entre sistemas
- **Control de acceso**: Solo administradores pueden crear agentes
- **Logging**: Registro completo de operaciones

## Migración desde Versión Anterior

### 1. Backup de Datos
```bash
# Hacer backup de la base de datos
docker-compose exec db pg_dump -U forensic sistema_forense > backup.sql
```

### 2. Ejecutar Migración
```bash
# El script de migración se ejecuta automáticamente
docker-compose exec app python migrate_database.py
```

### 3. Verificar Migración
```bash
# Verificar que las nuevas columnas existen
docker-compose exec app python -c "
from models import db, Usuario
from app import app
with app.app_context():
    print('Columnas de agente:', [col.name for col in Usuario.__table__.columns if 'agente' in col.name])
"
```

## Solución de Problemas

### 1. Agente No Responde
- Verificar que el contenedor esté ejecutándose
- Comprobar conectividad de red
- Revisar logs del agente

### 2. Error de Permisos
- Verificar que el contenedor tenga privilegios
- Comprobar acceso a dispositivos USB
- Revisar configuración de Docker

### 3. Error de Dependencias
- Reconstruir imagen del agente
- Verificar instalación de herramientas forenses
- Comprobar versiones de Python

## Monitoreo y Logs

### 1. Logs del Sistema
```bash
# Ver todos los logs
docker-compose logs -f

# Logs específicos del agente
docker-compose logs -f forensic_agent

# Logs de la aplicación principal
docker-compose logs -f app
```

### 2. Estado de Operaciones
- Panel de administración web
- API de estado de operaciones
- Logs de base de datos

### 3. Métricas de Rendimiento
- Uso de CPU y memoria
- Espacio en disco
- Operaciones concurrentes
- Tiempo de adquisición

## Desarrollo y Personalización

### 1. Agregar Nuevas Capacidades
- Modificar `capacidades_forenses` en el modelo
- Actualizar `forensic_agent.py`
- Agregar nuevos formatos de adquisición

### 2. Personalizar Interfaz
- Modificar templates HTML
- Actualizar CSS/JavaScript
- Agregar nuevas funcionalidades

### 3. Integración con Herramientas Externas
- Agregar nuevos endpoints API
- Implementar webhooks
- Conectar con sistemas externos

## Soporte y Contribución

Para reportar problemas o contribuir al proyecto:
1. Crear un issue en el repositorio
2. Describir el problema detalladamente
3. Incluir logs y configuración
4. Proporcionar pasos para reproducir

## Licencia

Este proyecto está bajo la licencia [especificar licencia].
