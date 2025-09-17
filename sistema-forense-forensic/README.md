# Sistema Forense - Stack Forense (Python 3.9)

## Descripción
Stack especializado para herramientas forenses con Python 3.9, optimizado para pyaff4, pyewf y formatos E01/AFF4.

## Archivos
- `Dockerfile` - Imagen base con Python 3.9 y herramientas forenses
- `docker-compose-forensic.yml` - Configuración del stack forense
- `forensic_agent.py` - Agente forense principal
- `requirements_forensic.txt` - Dependencias específicas

## Uso

### Iniciar Stack Forense
```bash
# Desde la carpeta sistema-forense-forensic
docker-compose -f docker-compose-forensic.yml up --build
```

### Detener Stack Forense
```bash
docker-compose -f docker-compose-forensic.yml down
```

### Ver Logs
```bash
docker-compose -f docker-compose-forensic.yml logs -f
```

## Requisitos
- El stack principal debe estar ejecutándose
- Red `forense_network` debe existir
- Base de datos PostgreSQL accesible

## Puertos
- `5001` - API del agente forense

## Volúmenes
- `/mnt/Respaldo/sistema-forense/forensic_data` - Datos forenses
- `/mnt/Respaldo/sistema-forense/logs` - Logs del sistema
- `/mnt/Respaldo/sistema-forense/temp` - Archivos temporales
