# Sistema de Archivos Distribuido P2P con Interoperabilidad DNS

Este proyecto implementa un sistema de archivos distribuido (DFS) resiliente y descentralizado en Python. Cuenta con una arquitectura personalizada que incluye servidores de nombres (DNS) locales y generales, mecanismos de bloqueo de archivos (locking) para consistencia en escrituras, y descubrimiento de pares.

## 🚀 Características

- **Arquitectura Híbrida**: Combina un DNS General (Coordinador) con DNS Locales para resolución de nombres distribuida.
- **Interoperabilidad**: Sistema de traducción (`Translator`) para comunicar diferentes protocolos de nodos.
- **Consistencia de Datos**: Implementación de bloqueos (Locks) y Check-in/Check-out para evitar condiciones de carrera.
- **Persistencia**: Almacenamiento local en cada nodo servidor.
- **Cliente Interactivo**: CLI basada en `prompt_toolkit` con autocompletado y menús.

## 📋 Requisitos

- Python 3.8+
- Dependencias listadas en `requirements.txt`

## 🛠️ Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/dist-fs-interop.git
cd dist-fs-interop
```

### 2. Crear y activar entorno virtual (opcional pero recomendado)
```bash
python -m venv venv

# En Windows:
venv\Scripts\activate

# En Unix/MacOS:
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

## ⚙️ Configuración

El sistema se configura a través de `network_config.json`. Define las IPs y puertos de:

- **DNS General**: El orquestador central.
- **Peers**: Cada nodo con su servidor de archivos y su DNS local asociado.

## ▶️ Ejecución

El proyecto incluye un lanzador maestro que coordina todos los procesos necesarios para una simulación local completa.

### Iniciar el Sistema Completo
```bash
python system_launcher.py
```

Selecciona la **Opción 4** (Iniciar sistema completo) para levantar el DNS General, los DNS Locales y los Servidores de Archivos automáticamente.

### Iniciar Cliente

En una nueva terminal (o usando la opción 5 del lanzador), ejecuta:
```bash
python src/client_distributed.py
```

## 🏗️ Arquitectura del Proyecto
```text
├── network_config.json       # Configuración global de la topología
├── system_launcher.py        # Script maestro de orquestación
├── dns_general.py            # Servidor de nombres principal
├── dns_local_service.py      # Servicio de DNS Local (Instanciable)
├── server_distributed.py     # Nodo servidor de archivos
├── src/
│   ├── client_distributed.py # Cliente CLI
│   ├── core/                 # Lógica de manejo de archivos
│   └── network/              # Capa de transporte y seguridad
└── archivos_server*/         # Directorios de almacenamiento (GitIgnored)
```

## 🤝 Contribución

Proyecto académico realizado colaborativamente.
