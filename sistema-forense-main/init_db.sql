-- Script de inicialización de la base de datos
-- Este archivo se ejecuta automáticamente al crear el contenedor

-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Crear tabla de agentes
CREATE TABLE IF NOT EXISTS agentes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre VARCHAR(100) NOT NULL,
    ip_address INET NOT NULL,
    puerto INTEGER DEFAULT 8080,
    sistema_operativo VARCHAR(50),
    version_agente VARCHAR(20),
    estado VARCHAR(20) DEFAULT 'offline',
    ultima_conexion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    configuracion JSONB,
    activo BOOLEAN DEFAULT true
);

-- Crear tabla de tareas
CREATE TABLE IF NOT EXISTS tareas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agente_id UUID REFERENCES agentes(id),
    tipo VARCHAR(50) NOT NULL,
    comando TEXT NOT NULL,
    parametros JSONB,
    estado VARCHAR(20) DEFAULT 'pendiente',
    resultado TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_ejecucion TIMESTAMP,
    fecha_finalizacion TIMESTAMP,
    error TEXT
);

-- Crear tabla de logs del sistema
CREATE TABLE IF NOT EXISTS logs_sistema (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nivel VARCHAR(20) NOT NULL,
    mensaje TEXT NOT NULL,
    modulo VARCHAR(50),
    agente_id UUID REFERENCES agentes(id),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_agentes_estado ON agentes(estado);
CREATE INDEX IF NOT EXISTS idx_agentes_activo ON agentes(activo);
CREATE INDEX IF NOT EXISTS idx_tareas_agente ON tareas(agente_id);
CREATE INDEX IF NOT EXISTS idx_tareas_estado ON tareas(estado);
CREATE INDEX IF NOT EXISTS idx_logs_fecha ON logs_sistema(fecha);

-- Insertar datos de prueba
INSERT INTO agentes (nombre, ip_address, sistema_operativo, version_agente) 
VALUES 
    ('Agente-Test-001', '192.168.1.100', 'Windows 10', '1.0.0'),
    ('Agente-Test-002', '192.168.1.101', 'Ubuntu 20.04', '1.0.0')
ON CONFLICT DO NOTHING;
