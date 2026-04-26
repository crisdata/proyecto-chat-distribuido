# Chat Privado Distribuido — Grupo 4

Sistema de chat distribuido con comunicación privada entre usuarios,
inteligencia artificial local y arquitectura completamente contenerizada.

---

## ¿Qué hace este sistema?

Permite que múltiples usuarios se registren y conversen entre sí mediante
mensajes privados. Incluye un nodo de inteligencia artificial (Ollama
llama3.2:3b) que participa como un usuario más del chat, respondiendo
preguntas y manteniendo contexto de la conversación.

---

## Arquitectura

    ┌─────────────────────────────────────────────────────────┐
    │                    Docker Network                        │
    │                                                         │
    │  ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │
    │  │  Nginx   │───▶│ FastAPI  │───▶│    MariaDB 11    │  │
    │  │  :80     │    │  :8000   │    │    (chat_db)     │  │
    │  │(Frontend)│    │(chat_api)│    └──────────────────┘  │
    │  └──────────┘    │          │───▶┌──────────────────┐  │
    │                  │          │    │    Redis 7        │  │
    │                  │          │    │  (chat_redis)    │  │
    │                  │          │───▶└──────────────────┘  │
    │                  └──────────┘    ┌──────────────────┐  │
    │                        │         │  Ollama llama3.2  │  │
    │                        └────────▶│  (chat_ollama)   │  │
    │                                  └──────────────────┘  │
    └─────────────────────────────────────────────────────────┘

| Componente | Tecnología | Rol |
|---|---|---|
| Frontend | React 19 + Vite 8 + Tailwind 3 + Nginx | Interfaz de usuario |
| API | FastAPI 0.135 + Uvicorn | Servidor principal |
| Base de datos | MariaDB 11 + aiomysql | Persistencia |
| Caché | Redis 7 | Locks distribuidos y caché |
| IA | Ollama llama3.2:3b | Nodo participante del chat |

---

## Requisitos

- Docker Engine 24+ o Docker Desktop
- Docker Compose v2
- 4GB de RAM disponibles (el modelo de IA ocupa ~2GB)
- Conexión a internet para la primera instalación

> **Usuarios de Windows:** Docker Desktop debe estar abierto y corriendo
> antes de ejecutar cualquier comando. Los comandos se ejecutan desde
> una terminal WSL2 (Ubuntu), no desde PowerShell ni CMD.

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

El archivo `.env.example` ya contiene valores funcionales para desarrollo
local. Edítalos solo si necesitas cambiar contraseñas o puertos.

### 3. Levantar todos los servicios

```bash
docker compose up --build -d
```

Este comando construye las imágenes del backend y frontend, descarga las
imágenes de MariaDB, Redis y Ollama, y levanta los 5 contenedores en
segundo plano. La primera ejecución tarda varios minutos.

### 4. Descargar el modelo de inteligencia artificial

Este paso solo es necesario la primera vez. El modelo se descarga dentro
del contenedor y queda almacenado en el volumen `proyecto1_ollama_data`.
Las siguientes veces que levantes el sistema el modelo ya estará disponible.

```bash
docker exec -it chat_ollama ollama pull llama3.2:3b
```

La descarga es de aproximadamente 2GB y puede tardar varios minutos
dependiendo de la velocidad de la conexión.

### 5. Verificar que todo está corriendo

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Deberías ver los 5 contenedores con estado `Up`:
NAMES           STATUS          PORTS
chat_frontend   Up X minutes    0.0.0.0:80->80/tcp
chat_api        Up X minutes    8000/tcp
chat_redis      Up X minutes    6379/tcp
chat_db         Up X minutes    3306/tcp
chat_ollama     Up X minutes    11434/tcp

### 6. Abrir la aplicación

Abre el navegador en: **http://localhost**

Para probar el chat entre dos usuarios abre una segunda pestaña en la
misma dirección y regístrate con un nombre diferente. Si cierras el
navegador y vuelves a ingresar con el mismo nombre, el sistema te
reconoce automáticamente.

---

## Endpoints de la API

La documentación interactiva (Swagger) está disponible internamente.
Para acceder durante desarrollo local sin Docker, levanta solo el backend
con `uvicorn app.main:app --reload` y abre **http://localhost:8000/docs**.

| Método | Endpoint | Descripción |
|---|---|---|
| GET | / | Estado del sistema |
| POST | /usuarios | Registrar o reingresar usuario |
| GET | /usuarios | Listar todos los usuarios |
| POST | /mensaje_privado | Enviar mensaje privado |
| GET | /conversacion/{id} | Historial de mensajes recibidos |
| GET | /conversacion/{id}/{contacto_id} | Conversación bilateral completa |
| GET | /no_leidos/{id} | Mensajes no leídos |
| POST | /ia/mensaje | Enviar mensaje al nodo IA |
| GET | /ia/estado | Verificar disponibilidad del nodo IA |

---

## Estructura del proyecto
proyecto-chat-distribuido/
├── app/
│   ├── main.py           # Punto de entrada y ciclo de vida
│   ├── models.py         # Modelos Pydantic
│   ├── database.py       # Pool de conexiones MariaDB
│   ├── cache.py          # Cliente Redis y locks distribuidos
│   └── routers/
│       ├── usuarios.py   # Registro y listado de usuarios
│       ├── mensajes.py   # Mensajes privados y conversaciones
│       └── ia.py         # Nodo IA Ollama
├── frontend/
│   ├── src/
│   │   ├── components/   # Registro, Sidebar, ListaContactos, Chat, Mensaje
│   │   ├── services/     # api.js — llamadas centralizadas al backend
│   │   ├── App.jsx       # Componente raíz y estado global
│   │   └── main.jsx      # Punto de entrada React
│   ├── Dockerfile        # Build multistage: Node → Nginx
│   └── nginx.conf        # Proxy /api y SPA fallback
├── docker-compose.yml    # Orquestación de los 5 servicios
├── Dockerfile            # Imagen del backend Python
├── requirements.txt      # Dependencias Python
└── .env.example          # Variables de entorno de referencia

---

## Comandos útiles

```bash
# Ver logs de un contenedor específico
docker logs chat_api --tail 50

# Ver logs en tiempo real
docker logs chat_api -f

# Verificar modelo de IA instalado
docker exec chat_ollama ollama list

# Apagar todos los servicios conservando los datos
docker compose down

# Apagar y eliminar todos los datos
docker compose down -v

# Reiniciar un contenedor específico
docker compose restart api
```

---

## Conceptos distribuidos implementados

**Locks distribuidos con Redis** — el registro de usuarios usa un lock con
token UUID único para evitar condiciones de carrera cuando dos usuarios
intentan registrarse con el mismo nombre simultáneamente.

**Caché con doble índice** — los usuarios se cachean en Redis por ID y por
nombre, reduciendo consultas a MariaDB en validaciones frecuentes.

**Nodo lógico de IA** — Ollama se registra como usuario del sistema al
arrancar, demostrando que la arquitectura soporta nodos no humanos sin
modificaciones al protocolo base.

**Pool de conexiones asíncrono** — aiomysql gestiona un pool de conexiones
compartido entre todos los endpoints, evitando abrir y cerrar conexiones
en cada solicitud.

---

## Próximos pasos — Corte 3

- Autenticación con JWT y contraseñas
- WebSockets para mensajes en tiempo real
- Salas de chat grupales
- Panel de monitoreo del sistema
- Contador de no leídos por contacto individual