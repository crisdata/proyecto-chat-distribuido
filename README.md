# Chat Privado Distribuido — Grupo 4

Sistema de chat distribuido con comunicación privada entre usuarios,
inteligencia artificial local y arquitectura completamente contenerizada.

---

## ¿Qué hace este sistema?

Permite que múltiples usuarios se registren y conversen entre sí mediante
mensajes privados en tiempo real. Incluye un nodo de inteligencia artificial
(Ollama llama3.2:3b) que participa como un usuario más del chat. Los mensajes
se entregan instantáneamente via WebSocket y el sistema de notificaciones
está desacoplado mediante RabbitMQ.

---

## Arquitectura

| Componente | Tecnología | Red | Rol |
|---|---|---|---|
| Frontend | React 19 + Vite 8 + Tailwind 3 + Nginx | public | Interfaz de usuario |
| API | FastAPI 0.135 + Uvicorn | public + app + data | Servidor principal |
| Base de datos | MariaDB 11 | data | Persistencia |
| Caché | Redis 7 | data | Locks distribuidos y caché |
| IA | Ollama llama3.2:3b | data | Nodo participante del chat |
| Mensajería | RabbitMQ 3.13 | app | Broker de mensajes asíncrono |
| Worker | Python asyncio | app + data | Procesa notificaciones |

---

## Segmentación de redes

El sistema implementa tres redes Docker aisladas siguiendo las mejores
prácticas de seguridad recomendadas por OWASP:

- **public_network** — Red de entrada. Contiene el frontend y la API. Es la única red con acceso desde el exterior.
- **app_network** (internal) — Contiene RabbitMQ y el worker. Bloqueada al exterior.
- **data_network** (internal) — Contiene MariaDB, Redis y Ollama. Completamente aislada del exterior.

---

## Requisitos

- Docker Engine 24+ o Docker Desktop
- Docker Compose v2
- 4GB de RAM disponibles (el modelo de IA ocupa ~2GB)
- Conexión a internet para la primera instalación

> **Usuarios de Windows:** Docker Desktop debe estar abierto y corriendo antes de ejecutar cualquier comando. Los comandos se ejecutan desde una terminal WSL2 (Ubuntu), no desde PowerShell ni CMD.

---

## Instalación y ejecución

### 1. Clonar el repositorio

```bash
git clone https://github.com/crisdata/proyecto-chat-distribuido.git
cd proyecto-chat-distribuido
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

El archivo `.env.example` ya contiene valores funcionales para desarrollo local. No es necesario editar nada para la primera ejecución.

### 3. Levantar todos los servicios

```bash
docker compose up --build -d
```

Este comando construye las imágenes, descarga las dependencias y levanta los 7 contenedores en segundo plano. La primera ejecución tarda varios minutos.

### 4. Descargar el modelo de inteligencia artificial

> Este paso solo es necesario la primera vez. El modelo queda almacenado en el volumen `proyecto1_ollama_data` y no necesita descargarse de nuevo.

```bash
docker exec -it chat_ollama ollama pull llama3.2:3b
```

La descarga es de aproximadamente 2GB y puede tardar varios minutos.

### 5. Verificar que todo está corriendo

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Networks}}"
```

Resultado esperado:

```
NAMES             STATUS           NETWORKS
chat_frontend     Up X minutes     proyecto1_public_network
chat_api          Up X minutes     proyecto1_app_network, proyecto1_data_network, proyecto1_public_network
chat_rabbitmq     Up X minutes     proyecto1_app_network, proyecto1_public_network
chat_worker       Up X minutes     proyecto1_app_network, proyecto1_data_network
chat_redis        Up X minutes     proyecto1_data_network
chat_db           Up X minutes     proyecto1_data_network
chat_ollama       Up X minutes     proyecto1_data_network
```

### 6. Abrir la aplicación

Abre el navegador en: **http://localhost**

Para probar el chat entre dos usuarios abre una segunda pestaña en la misma dirección y regístrate con un nombre diferente. Si cierras el navegador y vuelves a ingresar con el mismo nombre, el sistema te reconoce automáticamente.

### 7. Panel de administración RabbitMQ (opcional)

Para ver el estado de las colas y conexiones en tiempo real abre: **http://localhost:15672**

- Usuario: `guest`
- Contraseña: `guest`

---

## Endpoints de la API

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/` | Estado del sistema |
| POST | `/usuarios` | Registrar o reingresar usuario |
| GET | `/usuarios` | Listar todos los usuarios |
| POST | `/mensaje_privado` | Enviar mensaje privado |
| GET | `/conversacion/{id}` | Historial de mensajes recibidos |
| GET | `/conversacion/{id}/{contacto_id}` | Conversación bilateral completa |
| GET | `/no_leidos/{id}` | Mensajes no leídos |
| POST | `/ia/mensaje` | Enviar mensaje al nodo IA |
| GET | `/ia/estado` | Verificar disponibilidad del nodo IA |
| WS | `/ws/{usuario_id}` | Conexión WebSocket en tiempo real |

---

## Estructura del proyecto

```
proyecto-chat-distribuido/
├── app/
│   ├── main.py              # Punto de entrada y ciclo de vida
│   ├── models.py            # Modelos Pydantic
│   ├── database.py          # Pool de conexiones MariaDB
│   ├── cache.py             # Cliente Redis y locks distribuidos
│   ├── queue.py             # Conexión RabbitMQ y publicación
│   ├── worker.py            # Worker que consume la cola
│   └── routers/
│       ├── usuarios.py      # Registro y listado de usuarios
│       ├── mensajes.py      # Mensajes privados y conversaciones
│       ├── ia.py            # Nodo IA Ollama
│       ├── websocket.py     # ConnectionManager y endpoint WS
│       └── interno.py       # Endpoints internos para el worker
├── frontend/
│   ├── src/
│   │   ├── components/      # Registro, Sidebar, ListaContactos, Chat, Mensaje
│   │   ├── services/        # api.js — llamadas centralizadas al backend
│   │   ├── App.jsx          # Componente raíz y estado global
│   │   └── main.jsx         # Punto de entrada React
│   ├── Dockerfile           # Build multistage: Node → Nginx
│   └── nginx.conf           # Proxy /api, /ws y SPA fallback
├── docker-compose.yml       # Orquestación de los 7 servicios y 3 redes
├── Dockerfile               # Imagen del backend Python
├── Dockerfile.worker        # Imagen del worker RabbitMQ
├── requirements.txt         # Dependencias Python
└── .env.example             # Variables de entorno de referencia
```

---

## Comandos útiles

```bash
# Ver contenedores con sus redes asignadas
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Networks}}"

# Ver logs en tiempo real
docker logs chat_worker -f
docker logs chat_api -f

# Verificar modelo de IA instalado
docker exec chat_ollama ollama list

# Limpiar datos para demo
docker exec -it chat_db mariadb -u chat_user -pchat1234 chat_db \
  -e "DELETE FROM mensajes; DELETE FROM usuarios;"
docker compose restart api

# Apagar conservando datos
docker compose down

# Apagar eliminando todos los datos
docker compose down -v

# Reconstruir un contenedor específico
docker compose up --build -d api
```

---

## Flujo de un mensaje en tiempo real

```
Usuario A envía mensaje
        |
        v
POST /mensaje_privado
        |
        +-- Valida con Redis
        +-- Persiste en MariaDB  <-- fuente de verdad
        +-- Publica en RabbitMQ
        +-- Retorna 201
                |
                v  (asíncrono)
        Worker consume evento
                |
                +-- Llama POST /interno/notificar
                        |
                        v
                API notifica via WebSocket
                        |
                        v
                Usuario B ve el mensaje
```

---

## Conceptos distribuidos implementados

- **Locks distribuidos con Redis** — evita condiciones de carrera en registros simultáneos con token UUID único.
- **Caché con doble índice** — usuarios cacheados por ID y nombre, reduciendo consultas a MariaDB.
- **Nodo lógico de IA** — Ollama se registra como usuario del sistema al arrancar.
- **Pool de conexiones asíncrono** — aiomysql gestiona un pool compartido entre todos los endpoints.
- **WebSocket con reconexión automática** — backoff exponencial desde 1s hasta 30s con indicador visual de estado.
- **Mensajería asíncrona con RabbitMQ** — la API desacopla la persistencia de las notificaciones.
- **Segmentación de redes por capas** — tres redes Docker con aislamiento progresivo según OWASP.

---

## Próximos pasos

- Autenticación con JWT y contraseñas
- Salas de chat grupales
- Panel de monitoreo del sistema
- Acceso desde red local (múltiples usuarios en la misma red)
