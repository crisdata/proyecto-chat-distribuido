# Chat Privado Distribuido

Sistema de chat distribuido con comunicación privada entre usuarios,
inteligencia artificial local y arquitectura completamente contenerizada.

---

## ¿Qué hace este sistema?

Permite que múltiples usuarios se registren y conversen entre sí mediante
mensajes privados en tiempo real. Incluye un nodo de inteligencia artificial
(Ollama llama3.2:3b) que participa como un usuario más del chat. Los mensajes
se entregan instantáneamente vía WebSocket y el sistema de notificaciones
está desacoplado mediante RabbitMQ.

Además, el sistema implementa observabilidad completa: cuatro paneles web
permiten ver los logs, las colas de mensajes, la base de datos en caché
y administrar todo el entorno Docker en tiempo real.

---

## Características principales

- **Chat privado entre usuarios** con persistencia en MariaDB
- **Nodo de IA local** (Ollama llama3.2:3b) como participante del chat
- **Notificaciones en tiempo real** vía WebSocket
- **Mensajería desacoplada** con RabbitMQ y worker dedicado
- **Autenticación JWT** en cada conexión WebSocket y endpoint sensible
- **Locks distribuidos atómicos** en Redis con scripts Lua
- **Tres redes Docker segmentadas** siguiendo OWASP (capa pública, aplicación, datos)
- **Worker robusto** con reintentos exponenciales ante fallos transitorios
- **Trazabilidad completa** mediante `request_id` que viaja por todo el sistema
- **Observabilidad web** con Dozzle, Redis Commander, RabbitMQ y Portainer
- **Operación simplificada** mediante Makefile con comandos cortos

---

## Arquitectura del sistema

El proyecto está compuesto por diez servicios Docker organizados en tres
redes aisladas:

```
┌────────────────────────────────────────────────────────────────────┐
│                       public_network                                │
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌─────────┐    ┌──────────────┐ │
│  │  Nginx   │───▶│ FastAPI  │    │ Dozzle  │    │    Redis     │ │
│  │  :80     │ WS │  :8000   │    │  :9999  │    │  Commander   │ │
│  │(Frontend)│    │(chat_api)│    │ (logs)  │    │    :8081     │ │
│  └──────────┘    └────┬─────┘    └─────────┘    └──────┬───────┘ │
│                       │                                  │         │
│  ┌────────────┐       │                                  │         │
│  │ Portainer  │       │                                  │         │
│  │   :9000    │       │                                  │         │
│  └────────────┘       │                                  │         │
└──────────────────────┬┴────────────────────────────────┬─────────┘
                       │                                  │
         ┌─────────────┼──────────────┐                  │
         │             │              │                   │
┌────────▼─────────┐   │   ┌──────────▼──────────────────▼───────┐
│  app_network     │   │   │       data_network                  │
│  (internal)      │   │   │       (internal)                    │
│                  │   │   │                                      │
│  ┌────────────┐  │   │   │  ┌─────────┐  ┌───────┐            │
│  │  RabbitMQ  │  │   │   │  │MariaDB11│  │Redis 7│            │
│  │  :5672     │  │   │   │  └─────────┘  └───────┘            │
│  │ Panel:15672│  │   │   │  ┌────────────────────┐            │
│  └─────┬──────┘  │   │   │  │ Ollama llama3.2:3b │            │
│        │         │   │   │  └────────────────────┘            │
│  ┌─────▼──────┐  │   │   └──────────────────────────────────────┘
│  │  Worker    │  │   │
│  └────────────┘  │   │
└──────────────────┘   │
```

### Componentes y responsabilidades

| Componente | Tecnología | Red | Rol |
|---|---|---|---|
| Frontend | React 19 + Vite + Tailwind + Nginx | public | Interfaz de usuario |
| API | FastAPI 0.135 + Uvicorn | public + app + data | Servidor principal |
| Base de datos | MariaDB 11 | data | Persistencia |
| Caché y locks | Redis 7 | data | Coordinación distribuida |
| IA | Ollama llama3.2:3b | data | Nodo participante del chat |
| Mensajería | RabbitMQ 3.13 | app | Broker de eventos asíncronos |
| Worker | Python asyncio + aio-pika | app + data | Procesa notificaciones |
| Dozzle | amir20/dozzle | (socket Docker) | Visualizador web de logs |
| Redis Commander | rediscommander/redis-commander | public + data | Explorador web de Redis |
| Portainer | portainer/portainer-ce | (socket Docker) | Administrador web de Docker |

### Segmentación de redes

Tres redes Docker con aislamiento progresivo siguiendo recomendaciones OWASP:

- **public_network** — Capa de entrada. Único punto accesible desde el navegador.
- **app_network** — Capa de mensajería. Marcada como `internal: true` (sin salida a internet).
- **data_network** — Capa de datos. Marcada como `internal: true` (totalmente aislada del exterior).

---

## Requisitos previos

Antes de instalar el proyecto, asegúrate de tener lo siguiente en tu computadora:

- **Docker Desktop** instalado y funcionando
  - Windows o Mac: descarga desde https://www.docker.com/products/docker-desktop
  - Linux: instala Docker Engine y Docker Compose desde el repositorio oficial
- **Docker Compose v2** (incluido en Docker Desktop)
- **4 GB de RAM libre** (el modelo de IA ocupa ~2 GB)
- **Conexión a internet** para la primera instalación
- **Git** para clonar el repositorio
- **Make** para usar los comandos abreviados (opcional pero recomendado)

### Notas específicas por sistema operativo

**Usuarios de Windows:**
- Docker Desktop debe estar abierto y funcionando antes de cualquier comando
- Usa WSL2 (Subsistema de Windows para Linux) como terminal
- Los comandos NO se ejecutan en PowerShell ni en CMD, siempre en una terminal Ubuntu/WSL
- Instala `make` con: `sudo apt install make`

**Usuarios de Mac y Linux:**
- Cualquier terminal estándar funciona
- `make` viene preinstalado en la mayoría de distribuciones Linux

---

## Instalación paso a paso

Sigue cada paso en orden. Si tienes dudas en alguno, no avances hasta resolverlo.

### Paso 1 — Clonar el repositorio

Abre tu terminal y ejecuta:

```bash
git clone https://github.com/crisdata/proyecto-chat-distribuido.git
cd proyecto-chat-distribuido
```

### Paso 2 — Configurar las variables de entorno

El proyecto necesita un archivo `.env` con configuraciones secretas. Copiamos
el archivo de ejemplo:

```bash
cp .env.example .env
```

Ahora necesitas generar **dos secretos aleatorios** para la seguridad del sistema.
Ejecuta estos dos comandos exactamente como están:

```bash
echo "JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" >> .env
echo "WORKER_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" >> .env
```

Verifica que se agregaron correctamente al archivo:

```bash
tail -3 .env
```

Deberías ver dos líneas con valores largos de letras y números:

```
JWT_SECRET=k3FdR9_aBcDeFgHiJkLmNoPqRsTuVwXyZ012345...
WORKER_SECRET=p7Qw_xYz1aBcDe2FgHiJkLm3NoPqRsTuVw4...
```

> ⚠️ **Importante:** estos secretos son únicos para tu instalación. No los compartas
> ni los subas a repositorios públicos. Por eso `.env` está en `.gitignore`.

### Paso 3 — Levantar los servicios

Construye y arranca todos los contenedores. Tienes dos opciones equivalentes:

**Opción recomendada — con Makefile:**

```bash
make up
```

**Opción alternativa — con Docker Compose directamente:**

```bash
docker compose up --build -d
```

La primera ejecución tarda varios minutos porque descarga imágenes y
construye el frontend. Verás muchas líneas en la terminal — es normal.

Al finalizar, `make up` imprime un resumen con las URLs de todos los servicios
disponibles.

### Paso 4 — Verificar que todo está funcionando

Espera unos 30 segundos para que todos los servicios pasen sus chequeos
de salud. Luego ejecuta:

```bash
make ps
```

O alternativamente:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Deberías ver los 10 contenedores en estado `Up`:

```
NAMES                  STATUS
chat_portainer         Up X seconds
chat_frontend          Up X seconds
chat_redis_commander   Up X seconds
chat_dozzle            Up X seconds
chat_worker            Up X seconds
chat_api               Up X seconds
chat_rabbitmq          Up X seconds (healthy)
chat_redis             Up X seconds (healthy)
chat_db                Up X seconds (healthy)
chat_ollama            Up X seconds (healthy)
```

### Paso 5 — Descargar el modelo de inteligencia artificial

Este paso solo es necesario la primera vez. El modelo se queda almacenado
en un volumen Docker y sobrevive a reinicios.

> ⚠️ **Importante:** el contenedor de Ollama está en una red aislada (`data_network`)
> que no tiene acceso a internet por diseño de seguridad. Para descargar el modelo
> debemos conectarlo temporalmente a la red pública, descargar, y volver a aislarlo.

**Opción recomendada — con Makefile (automatiza todo el procedimiento):**

```bash
make pull-model
```

Este comando conecta Ollama a la red pública, descarga el modelo, lo desconecta
y muestra la lista de modelos disponibles para confirmar. Todo en un solo paso.

**Opción alternativa — manualmente:**

```bash
docker network connect proyecto1_public_network chat_ollama
docker exec -it chat_ollama ollama pull llama3.2:3b
docker network disconnect proyecto1_public_network chat_ollama
docker exec chat_ollama ollama list
```

Al terminar deberías ver una línea con el modelo descargado:

```
NAME            ID              SIZE      MODIFIED
llama3.2:3b     a80c4f17acd5    2.0 GB    X seconds ago
```

### Paso 6 — Abrir la aplicación

Ya está todo listo. Abre tu navegador favorito en:

**http://localhost**

Verás la pantalla de registro. Escribe cualquier nombre y entra al chat.

Para probar el chat entre dos usuarios, abre una segunda pestaña en modo
incógnito (Ctrl+Shift+N) e ingresa con un nombre diferente. Verás al otro
usuario aparecer en la lista de contactos automáticamente.

---

## Herramientas de observabilidad

El sistema viene con cuatro paneles web que permiten ver lo que pasa por dentro
en tiempo real. No requieren instalación adicional, ya están corriendo.

### Dozzle — Logs unificados

**URL:** http://localhost:9999

Muestra los logs de todos los contenedores en una interfaz limpia y en vivo.
Es la herramienta más útil para depurar y para presentaciones.

**Funciones útiles:**
- Lista de contenedores a la izquierda
- Click en cualquier contenedor muestra sus logs en vivo
- Filtro de texto en la parte superior
- Botón para ver varios contenedores a la vez

**Caso de uso:** envía un mensaje desde la app, copia el `request_id` que
aparece en los logs de la API, y pégalo en el buscador de Dozzle para ver
la cadena completa de procesamiento de ese mensaje.

### Redis Commander — Explorador de Redis

**URL:** http://localhost:8081

Permite inspeccionar las claves almacenadas en Redis (cache, locks, sesiones,
contadores). Útil para entender qué guarda el sistema en tiempo real.

**Claves típicas que verás:**

| Patrón | Significado |
|---|---|
| `usuario:<uuid>` | Caché del nombre del usuario |
| `sesion:<uuid>` | Token JWT activo |
| `lock:registro:<nombre>` | Lock distribuido durante registro |
| `no_leidos:<uuid>` | Contador de mensajes no leídos |
| `ia:id` | UUID del nodo IA |

### RabbitMQ Management — Panel del broker

**URL:** http://localhost:15672
**Usuario:** `guest`
**Contraseña:** `guest`

Muestra las colas, conexiones, consumidores y tráfico de mensajes.

**Sección útil:** pestaña **Queues** → click en `mensajes` para ver el tráfico
de notificaciones del chat en tiempo real.

### Portainer — Administrador web de Docker

**URL:** http://localhost:9000

Interfaz web completa para administrar todo el entorno Docker desde el navegador.
Mientras Dozzle se enfoca solo en logs, Portainer ofrece una visión integral
del sistema y permite ejecutar acciones administrativas sin terminal.

**Funciones útiles:**
- Ver los 10 contenedores con su estado, CPU y memoria en tiempo real
- Reiniciar, detener o iniciar contenedores con un clic
- Inspeccionar imágenes, volúmenes y redes Docker
- Ver el stack `proyecto1` como una unidad lógica
- Detectar automáticamente contenedores caídos o con problemas

**Primer ingreso:** Portainer pedirá crear un usuario administrador con
contraseña de mínimo 12 caracteres. Luego selecciona el entorno **"Local"**
para administrar el Docker del host.

**Caso de uso:** para demostrar resiliencia del sistema, entra a la sección
**Containers**, selecciona el contenedor `chat_worker`, click en **Restart**,
y observa cómo se reconecta automáticamente a RabbitMQ sin afectar al resto
de servicios.

---

## Cómo usar la trazabilidad con request_id

Cada vez que un usuario envía un mensaje, el sistema genera un identificador
único (request_id) de 8 caracteres que viaja por todos los componentes.
Esto permite seguir un mensaje desde que entra hasta que se entrega.

**Demostración de trazabilidad:**

1. Abre Dozzle en http://localhost:9999
2. En la app, envía un mensaje
3. Ve a Dozzle → `chat_api` → busca una línea como:

```
   2026-XX-XX ... INFO - [queue] [b7d4a2e1] Evento publicado en cola 'mensajes'
```

4. Copia el ID entre corchetes (en el ejemplo, `b7d4a2e1`)
5. Pega ese ID en el buscador de Dozzle
6. Cambia entre `chat_api` y `chat_worker` y verás las cinco líneas
   correspondientes al recorrido completo del mensaje, todas con el mismo ID

---

## Comandos útiles del día a día

El proyecto incluye un **Makefile** que define atajos para las operaciones
más frecuentes. Es la forma recomendada de operar el sistema porque evita
escribir comandos largos y reduce errores de tipeo.

Para ver todos los comandos disponibles con su descripción:

```bash
make help
```

### Comandos principales

| Comando | Qué hace | Equivalente Docker |
|---|---|---|
| `make up` | Construye y arranca todo el sistema en segundo plano | `docker compose up --build -d` |
| `make down` | Detiene todos los servicios conservando datos | `docker compose down` |
| `make restart` | Reinicia todos los servicios (down + up) | `docker compose down && up --build -d` |
| `make logs` | Muestra los logs de todos los servicios en vivo | `docker compose logs -f` |
| `make ps` | Muestra el estado de los contenedores | `docker ps` |
| `make status` | Alias de `make ps` | — |

### Comandos avanzados

| Comando | Qué hace | Cuándo usarlo |
|---|---|---|
| `make build` | Reconstruye las imágenes sin levantar los contenedores | Tras cambios sin querer arrancar |
| `make pull-model` | Descarga el modelo Ollama automáticamente | Instalación inicial o tras `make clean` |
| `make reset-db` | Limpia mensajes y usuarios para una demo | Antes de presentar |
| `make clean` | Detiene los servicios y borra TODOS los datos persistentes | Solo para resetear el proyecto de cero |

### Comandos de mantenimiento

| Comando | Qué hace | Cuándo usarlo |
|---|---|---|
| `make disk` | Muestra el uso de disco de Docker | Para diagnosticar acumulación de basura |
| `make prune` | Limpia build cache y volúmenes huérfanos | Mantenimiento semanal |
| `make prune-all` | Limpieza profunda con confirmación | Antes de entregas o instalaciones limpias |

> ⚠️ **Importante:** `make clean` borra los volúmenes con datos persistentes
> (BD, modelo IA, configuración de Portainer). Tras ejecutarlo deberás repetir
> el Paso 5 de la instalación para volver a descargar el modelo. Los comandos
> `prune` y `prune-all` son seguros y nunca tocan datos en uso.

### Comandos manuales sin Makefile

Si por alguna razón no puedes usar `make`, todos los comandos tienen su
equivalente directo con Docker Compose:

```bash
# Ver estado
docker ps --format "table {{.Names}}\t{{.Status}}"

# Ver logs en vivo de un contenedor específico
docker logs chat_api -f

# Reiniciar un servicio sin tocar los demás
docker compose restart api

# Apagar todos los servicios conservando los datos
docker compose down

# Apagar y borrar TODO (mensajes, usuarios, modelo de IA)
docker compose down -v

# Limpiar mensajes para una demo
docker exec -it chat_db mariadb -u chat_user -pchat1234 chat_db \
  -e "DELETE FROM mensajes; DELETE FROM usuarios;"
docker compose restart api

# Reconstruir un servicio después de cambiar código
docker compose up --build -d api
```

---

## Solución de problemas comunes

### "Cannot connect to the Docker daemon"

Docker Desktop no está corriendo. Ábrelo desde el menú de inicio y espera
a que aparezca el ícono activo en la barra de tareas. Reintenta el comando.

### "Bind for 0.0.0.0:XXXX failed: port is already allocated"

Otro proceso usa ese puerto. Comprueba si tienes algún contenedor viejo:

```bash
docker ps -a
docker rm -f <nombre-del-contenedor-viejo>
```

Si no es Docker, identifica qué proceso usa el puerto:

```bash
sudo lsof -i :15672    # cambia el número de puerto según el error
```

Y termínalo, o cambia el puerto en `docker-compose.yml`.

### "El nodo IA no está disponible"

Verifica que el modelo está descargado:

```bash
docker exec chat_ollama ollama list
```

Si la lista está vacía, repite el Paso 5 de la instalación con `make pull-model`.

### "Error al descargar el modelo: server misbehaving"

Es un problema de DNS. Asegúrate de haber conectado Ollama temporalmente
a la red pública antes de hacer el `pull`. El comando `make pull-model`
hace esto automáticamente.

### La API se reinicia en bucle al levantar

Probablemente faltan los secretos en `.env`. Verifica:

```bash
grep -E "JWT_SECRET|WORKER_SECRET" .env
```

Si no aparecen las dos líneas, ejecuta el Paso 2 de nuevo.

### "WORKER_SECRET no está definido"

Mismo problema que el anterior. Aplica la solución del Paso 2.

### El frontend muestra el HTML antiguo después de cambios

Caché del navegador. En DevTools (F12) → pestaña Network → marca "Disable cache"
y recarga con `Ctrl+Shift+R`. Si persiste, reconstruye sin caché:

```bash
docker compose build --no-cache frontend
docker compose up -d --force-recreate frontend
```

### Disco Docker lleno o muy grande

Tras varias iteraciones de desarrollo, el caché de Docker puede crecer
significativamente. Ejecuta:

```bash
make disk        # ver cuánto ocupa
make prune       # limpiar build cache y volúmenes huérfanos
```

Para una limpieza más profunda (antes de una entrega):

```bash
make prune-all
```

### "make: command not found"

`make` no está instalado. En Ubuntu o WSL2:

```bash
sudo apt update && sudo apt install make
```

En Mac:

```bash
xcode-select --install
```

## Despliegue automatizado (CI/CD)

![Build Status](https://github.com/crisdata/proyecto-chat-distribuido/actions/workflows/docker.yml/badge.svg)

El sistema cuenta con un pipeline de CI/CD implementado en GitHub Actions que
automatiza la construcción y publicación de las imágenes Docker cada vez que
se hace un push a la rama `main`.

### Imágenes publicadas en DockerHub

Las tres imágenes del sistema están disponibles públicamente:

- `crisdatap/vibe-api:latest` — Backend FastAPI con WebSocket
- `crisdatap/vibe-worker:latest` — Worker consumer de RabbitMQ
- `crisdatap/vibe-frontend:latest` — React 19 + Nginx (build multi-stage)

DockerHub: https://hub.docker.com/u/crisdatap

### Desplegar el sistema desde cualquier máquina

Cualquier máquina con Docker puede ejecutar el sistema completo **sin necesidad
de tener el código fuente**. Solo se requieren dos archivos:

1. **`docker-compose.prod.yml`** — define los servicios usando imágenes de DockerHub
2. **`.env`** — variables de entorno (basado en `.env.example`)

#### Pasos completos para despliegue remoto

```bash
# 1. Crear carpeta de despliegue
mkdir vibe-deploy && cd vibe-deploy

# 2. Descargar docker-compose.prod.yml del repositorio
curl -O https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/docker-compose.prod.yml

# 3. Descargar plantilla de variables
curl -O https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/.env.example
mv .env.example .env

# 4. Generar secretos únicos para esta instalación
echo "JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" >> .env
echo "WORKER_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" >> .env

# 5. Levantar el sistema (descarga imágenes desde DockerHub)
docker compose -f docker-compose.prod.yml up -d

# 6. Verificar que arrancó correctamente
docker ps

# 7. (Opcional) Descargar el modelo de IA para activar a Lumi
docker network connect vibe-deploy_public_network chat_ollama
docker exec -it chat_ollama ollama pull llama3.2:3b
docker network disconnect vibe-deploy_public_network chat_ollama
```

Acceder a la aplicación: **http://localhost**

> **Nota sobre Lumi:** sin descargar el modelo, Lumi (la IA) responde con
> mensajes de fallback empáticos en modo "reposando". Esto demuestra la
> resiliencia del sistema ante la ausencia de componentes opcionales.

### Comandos del Makefile para modo producción

| Comando | Descripción |
|---|---|
| `make prod-up` | Levanta el sistema descargando imágenes desde DockerHub |
| `make prod-down` | Detiene los contenedores conservando datos |
| `make prod-pull` | Actualiza las imágenes a la última versión publicada |
| `make prod-pull-model` | Descarga el modelo de IA para activar a Lumi |
| `make prod-logs` | Muestra logs del sistema en vivo |
| `make prod-status` | Estado de los contenedores |

### Arquitectura del pipeline CI/CD

```
Desarrollador → git push origin main
                       │
                       ▼
                 GitHub detecta push
                       │
                       ▼
        ┌──────────────────────────────────┐
        │   GitHub Actions (Ubuntu)         │
        │                                   │
        │   ┌─────────┐ ┌─────────┐ ┌─────┐│
        │   │ build-  │ │ build-  │ │build││
        │   │  api    │ │ worker  │ │front││
        │   └────┬────┘ └────┬────┘ └──┬──┘│
        │        │           │          │  │
        │        └───────────┼──────────┘  │
        │                    ▼              │
        │              notify-success       │
        └──────────────────┬───────────────┘
                           │
                           ▼ docker push
                      ┌─────────┐
                      │DockerHub│
                      └────┬────┘
                           │
                           ▼ docker pull
              Cualquier máquina con Docker
```

### ¿Qué automatiza el pipeline?

Cada push a `main` desencadena automáticamente:

1. **Checkout** del código del repositorio
2. **Login** a DockerHub usando secrets seguros
3. **Build** de las tres imágenes en paralelo
4. **Tag dual** con `latest` y SHA del commit (para trazabilidad)
5. **Push** de las imágenes a DockerHub
6. **Notificación** del resultado

**Tiempo del pipeline:** ~45 segundos con caché habilitado.

---

## Endpoints de la API

| Método | Endpoint | Autenticación | Descripción |
|---|---|---|---|
| GET | `/` | No | Estado del sistema |
| POST | `/usuarios` | No | Registrar o reingresar usuario |
| GET | `/usuarios` | No | Listar todos los usuarios |
| GET | `/usuarios/me` | JWT | Datos del usuario autenticado |
| POST | `/mensaje_privado` | JWT | Enviar mensaje privado |
| GET | `/conversacion/{id}` | No | Historial de mensajes recibidos |
| GET | `/conversacion/{id}/{contacto_id}` | No | Conversación bilateral completa |
| GET | `/no_leidos/{id}` | No | Mensajes no leídos del usuario |
| POST | `/ia/mensaje` | JWT | Enviar mensaje al nodo IA |
| GET | `/ia/estado` | No | Verificar disponibilidad del nodo IA |
| POST | `/interno/notificar` | Worker secret | Endpoint interno usado por el worker |
| WS | `/ws/{usuario_id}?token=<jwt>` | JWT | Conexión WebSocket en tiempo real |

---

## Estructura del proyecto

```
proyecto-chat-distribuido/
├── app/
│   ├── main.py                 # Punto de entrada y middleware HTTP
│   ├── auth.py                 # Autenticación JWT y secreto del worker
│   ├── models.py               # Modelos de datos Pydantic
│   ├── database.py             # Pool de conexiones MariaDB
│   ├── cache.py                # Redis: caché, locks, contadores, sesiones
│   ├── queue.py                # Conexión RabbitMQ y publicación
│   ├── worker.py               # Worker que consume la cola
│   ├── request_id.py           # ContextVar para trazabilidad
│   ├── logging_config.py       # Configuración central de logging
│   └── routers/
│       ├── usuarios.py         # Registro, listado, /me
│       ├── mensajes.py         # Mensajes privados y conversaciones
│       ├── ia.py               # Nodo IA Ollama
│       ├── websocket.py        # ConnectionManager y endpoint WS
│       └── interno.py          # Endpoint interno usado por el worker
├── frontend/
│   ├── src/
│   │   ├── components/         # Registro, Sidebar, ListaContactos, Chat, Mensaje
│   │   ├── services/
│   │   │   └── api.js          # Cliente HTTP y WebSocket
│   │   ├── App.jsx             # Componente raíz y restauración de sesión
│   │   └── main.jsx            # Punto de entrada React
│   ├── Dockerfile              # Build multistage: Node → Nginx
│   └── nginx.conf              # Proxy /api, /ws y SPA fallback
├── docker-compose.yml          # Orquestación de servicios y redes
├── Dockerfile                  # Imagen del backend Python
├── Dockerfile.worker           # Imagen del worker RabbitMQ
├── Makefile                    # Atajos para operación y mantenimiento
├── requirements.txt            # Dependencias Python
└── .env.example                # Variables de entorno de referencia
```

---

## Flujo de un mensaje en tiempo real

Cuando un usuario A envía un mensaje a un usuario B, el sistema ejecuta
los siguientes pasos:

```
1. Frontend de A → POST /mensaje_privado
                    ↓
2. API genera request_id [b7d4a2e1] (middleware HTTP)
                    ↓
3. API valida emisor y receptor en Redis (caché) o MariaDB
                    ↓
4. API persiste el mensaje en MariaDB (fuente de verdad)
                    ↓
5. API publica evento en RabbitMQ con request_id en el payload
                    ↓
6. API retorna 201 al frontend de A
                    ↓ (procesamiento asíncrono)
7. Worker consume el evento de RabbitMQ
                    ↓
8. Worker adopta el request_id del payload
                    ↓
9. Worker llama POST /interno/notificar con header X-Request-ID
                    ↓
10. API recibe y reconoce el request_id por el header
                    ↓
11. API incrementa contador de no leídos del receptor en Redis
                    ↓
12. API notifica al receptor B vía WebSocket
                    ↓
13. Frontend de B recibe la notificación y carga la conversación
```

Cada uno de los pasos del 1 al 12 produce un log con el **mismo request_id**,
lo que permite trazar el flujo completo en Dozzle.

---

## Conceptos distribuidos implementados

El proyecto cubre varios conceptos clave de sistemas distribuidos:

- **Locks distribuidos atómicos en Redis** — el registro de usuarios usa
  un script Lua para liberación atómica, evitando condiciones de carrera
  entre GET y DELETE.

- **Caché con doble índice** — los usuarios se cachean en Redis por ID
  y por nombre, reduciendo consultas a MariaDB.

- **Nodo lógico de IA** — Ollama se registra como usuario del sistema al
  arrancar, demostrando que la arquitectura soporta nodos no humanos sin
  modificaciones.

- **Pool de conexiones asíncrono** — aiomysql gestiona un pool compartido
  entre todos los endpoints.

- **WebSocket con reconexión automática** — backoff exponencial desde 1s
  hasta 30s máximo, con indicador visual de estado de conexión.

- **Mensajería asíncrona con RabbitMQ** — la API desacopla la persistencia
  de las notificaciones. El worker procesa eventos de forma independiente
  con reintentos exponenciales (máximo 3) antes de descartar.

- **Autenticación JWT** — tokens firmados con HS256, almacenados también
  en Redis para permitir revocación inmediata.

- **Trazabilidad mediante request_id** — identificador único por petición
  que viaja a través de HTTP, RabbitMQ y de vuelta a HTTP, usando
  ContextVar para aislamiento entre peticiones concurrentes.

- **Segmentación de redes por capas** — tres redes Docker con aislamiento
  progresivo siguiendo las recomendaciones OWASP.

- **Orquestación con un solo comando** — el sistema completo (10 servicios,
  3 redes, 4 volúmenes) se levanta con `make up`, demostrando los principios
  de Infrastructure as Code.

---

## Créditos

Proyecto desarrollado para el curso de **Programación
Distribuida** del programa de **Ingeniería de Sistemas**.