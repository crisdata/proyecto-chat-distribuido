# Chat Privado Distribuido — Grupo 4

Sistema de chat distribuido con comunicación privada entre usuarios,
inteligencia artificial local y arquitectura completamente contenerizada.

---

## ¿Qué hace este sistema?

Permite que múltiples usuarios se registren y conversen entre sí mediante
mensajes privados en tiempo real. Incluye un nodo de inteligencia artificial
(Ollama llama3.2:3b) que participa como un usuario más del chat. Los mensajes
se entregan instantáneamente vía WebSocket y el sistema de notificaciones
está desacoplado mediante RabbitMQ.

Además, el sistema implementa observabilidad completa: tres paneles web
permiten ver los logs, las colas de mensajes y la base de datos en caché
en tiempo real.

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
- **Observabilidad web** con Dozzle, Redis Commander y panel de RabbitMQ

---

## Arquitectura del sistema

El proyecto está compuesto por nueve servicios Docker organizados en tres
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

### Notas específicas por sistema operativo

**Usuarios de Windows:**
- Docker Desktop debe estar abierto y funcionando antes de cualquier comando
- Usa WSL2 (Subsistema de Windows para Linux) como terminal
- Los comandos NO se ejecutan en PowerShell ni en CMD, siempre en una terminal Ubuntu/WSL

**Usuarios de Mac y Linux:**
- Cualquier terminal estándar funciona

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

Construye y arranca todos los contenedores:

```bash
docker compose up --build -d
```

La primera ejecución tarda varios minutos porque descarga imágenes y
construye el frontend. Verás muchas líneas en la terminal — es normal.

### Paso 4 — Verificar que todo está funcionando

Espera unos 30 segundos para que todos los servicios pasen sus chequeos
de salud. Luego ejecuta:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Deberías ver los 9 contenedores en estado `Up`:

```
NAMES                  STATUS
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

Ejecuta estos comandos en orden:

```bash
# 1. Conectar Ollama temporalmente a la red con internet
docker network connect proyecto1_public_network chat_ollama

# 2. Descargar el modelo (tarda varios minutos, son ~2 GB)
docker exec -it chat_ollama ollama pull llama3.2:3b

# 3. Desconectar Ollama de la red pública (volver al aislamiento)
docker network disconnect proyecto1_public_network chat_ollama

# 4. Verificar que el modelo está disponible
docker exec chat_ollama ollama list
```

Deberías ver una línea con el modelo descargado:

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

El sistema viene con tres paneles web que permiten ver lo que pasa por dentro
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

### Ver el estado de todos los contenedores

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Ver logs en vivo de un contenedor específico

```bash
docker logs chat_api -f
```

Sale con `Ctrl+C`. También puedes ver los logs en Dozzle directamente.

### Reiniciar un servicio sin tocar los demás

```bash
docker compose restart api
```

### Apagar todos los servicios conservando los datos

```bash
docker compose down
```

### Apagar y borrar TODO (mensajes, usuarios, modelo de IA)

```bash
docker compose down -v
```

> ⚠️ Esto borra los volúmenes. La próxima vez que arranques tendrás que
> volver a descargar el modelo de IA siguiendo el Paso 5.

### Limpiar mensajes para una demo

```bash
docker exec -it chat_db mariadb -u chat_user -pchat1234 chat_db \
  -e "DELETE FROM mensajes; DELETE FROM usuarios;"
docker compose restart api
```

### Reconstruir un servicio después de cambiar código

```bash
docker compose up --build -d api
```

Cambia `api` por el nombre del servicio que modificaste.

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

Si la lista está vacía, repite el Paso 5 de la instalación.

### "Error al descargar el modelo: server misbehaving"

Es un problema de DNS. Asegúrate de haber conectado Ollama temporalmente
a la red pública antes de hacer el `pull`. Sigue el Paso 5 al pie de la letra.

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

---

## Créditos

Proyecto desarrollado por el **Grupo 4** para el curso de **Programación
Distribuida** del programa de **Ingeniería de Sistemas** de **COTECNOVA**.

Profesor: Jhon James Cano Sánchez