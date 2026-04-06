# Chat Privado Usuario-Usuario

---

## ¿Qué hace este sistema?

Sistema de chat distribuido que permite comunicación privada entre usuarios
registrados, con persistencia en MariaDB, sincronización distribuida mediante
Redis y un nodo de inteligencia artificial local (Ollama llama3.2:3b) como
participante del chat.

---

## Arquitectura

| Componente | Tecnología | Rol |
|---|---|---|
| API | FastAPI + Uvicorn | Servidor principal |
| Base de datos | MariaDB 11 | Persistencia de usuarios y mensajes |
| Caché | Redis 7 | Locks distribuidos y caché de usuarios |
| IA | Ollama llama3.2:3b | Nodo participante del chat |

---

## Requisitos

- Docker
- Docker Compose

---

## Instalación y ejecución

**1. Clonar el repositorio**
```bash
git clone https://github.com/crisdata/proyecto-chat-distribuido.git
cd proyecto-chat-distribuido
```

**2. Crear el archivo de variables de entorno**
```bash
cp .env.example .env
```

**3. Levantar todos los servicios**
```bash
docker compose up --build
```

**4. Abrir la documentación interactiva**
http://localhost:8000/docs

---

## Endpoints disponibles

| Método | Endpoint | Descripción |
|---|---|---|
| GET | / | Estado del sistema |
| POST | /usuarios | Registrar usuario |
| GET | /usuarios | Listar usuarios |
| POST | /mensaje_privado | Enviar mensaje privado |
| GET | /conversacion/{usuario_id} | Historial de mensajes |
| GET | /no_leidos/{usuario_id} | Mensajes no leídos |
| POST | /ia/mensaje | Enviar mensaje al nodo IA |

---

## Estructura del proyecto

proyecto-chat-distribuido/
├── app/
│   ├── main.py          # Punto de entrada y ciclo de vida
│   ├── models.py        # Modelos de datos con Pydantic
│   ├── database.py      # Conexión a MariaDB
│   ├── cache.py         # Conexión a Redis
│   └── routers/
│       ├── usuarios.py  # Endpoints de usuarios
│       ├── mensajes.py  # Endpoints de mensajes
│       └── ia.py        # Nodo IA (Ollama)
├── frontend/            # Interfaz visual
├── tests/               # Pruebas de concurrencia
├── docker-compose.yml   # Orquestación de contenedores
├── Dockerfile           # Imagen de la API
└── requirements.txt     # Dependencias

---

## Próximos pasos

- Autenticación con JWT
- WebSockets para mensajes en tiempo real
- Historial con contexto para la IA
- Salas grupales
- Panel de monitoreo del sistema