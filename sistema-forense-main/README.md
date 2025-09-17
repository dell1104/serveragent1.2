# Sistema Forense - Stack Principal (Python 3.13)

## Descripción
Stack principal del sistema forense con aplicación web, base de datos y servicios de soporte.

## Archivos
- `docker-compose.yml` - Configuración del stack principal
- `app.py` - Aplicación Flask principal
- `models.py` - Modelos de datos (Usuario/Agente unificado)
- `blueprints/` - Módulos de la aplicación
- `templates/` - Plantillas HTML
- `static/` - Archivos estáticos

## Uso

### Iniciar Stack Principal
```bash
# Desde la carpeta sistema-forense-main
docker-compose up --build
```

### Detener Stack Principal
```bash
docker-compose down
```

### Ver Logs
```bash
docker-compose logs -f
```

## Servicios
- **app** - Aplicación Flask (Puerto 5000)
- **db** - PostgreSQL (Puerto 5432)
- **redis** - Redis (Puerto 6379)
- **nginx** - Proxy reverso (Puerto 8080)

## Volúmenes
- `/mnt/Respaldo/sistema-forense` - Directorio principal
- `postgres_data` - Datos de PostgreSQL
- `redis_data` - Datos de Redis

## Red
- `forense_network` - Red compartida con el stack forense
