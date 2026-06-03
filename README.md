# Vibe — Red social universitaria con privacidad real

> Sistema distribuido de mensajería que combina chat privado entre usuarios
> con una compañera virtual con IA local llamada **Lumi**. Todo corre en tu
> propia máquina: ningún mensaje sale hacia servicios externos.

**Autores:** Cristian Giraldo & Sebastián Pérez  
**Curso:** Programación Distribuida  
**Repositorio:** https://github.com/crisdata/proyecto-chat-distribuido

[![Build Status](https://github.com/crisdata/proyecto-chat-distribuido/actions/workflows/docker.yml/badge.svg)](https://github.com/crisdata/proyecto-chat-distribuido/actions)

---

## Tabla de contenido

1. [Qué es Vibe](#qué-es-vibe)
2. [Qué incluye el sistema](#qué-incluye-el-sistema)
3. [Requisitos](#requisitos)
4. [Instalación en Windows](#instalación-en-windows)
5. [Cómo probar que funciona](#cómo-probar-que-funciona)
6. [Activar la IA (Lumi)](#activar-la-ia-lumi)
7. [Interfaces y observabilidad](#interfaces-y-observabilidad)
8. [Endpoints de la API](#endpoints-de-la-api)
9. [Comandos del Makefile](#comandos-del-makefile)
10. [Arquitectura](#arquitectura)
11. [CI/CD](#cicd)
12. [Solución de problemas](#solución-de-problemas)
13. [Estructura del proyecto](#estructura-del-proyecto)
14. [Instalación para desarrollo](#instalación-para-desarrollo)

---

## Qué es Vibe

Vibe es una aplicación de chat donde varios usuarios se registran y conversan
entre sí mediante mensajes privados en tiempo real. Incluye a **Lumi**, una
compañera virtual basada en un modelo de IA que corre localmente con Ollama:
ningún mensaje se envía a servicios de terceros.

El sistema está construido como una arquitectura distribuida de **10
contenedores Docker** repartidos en **3 redes aisladas**, con mensajería
asíncrona, caché, autenticación y observabilidad.

---

## Qué incluye el sistema

| Funcionalidad | Cómo está implementada |
|---|---|
| Login por correo | Inicio de sesión demo con email normalizado y nombre visible; el email no se expone en UI/API/JWT |
| Chat privado entre usuarios | Mensajes persistidos en MariaDB, autenticación JWT |
| Grupos públicos | Creación, búsqueda y chat en grupos abiertos sin administradores ni moderación |
| Compañera virtual Lumi | Ollama con `llama3.2:3b` en red aislada; responde con mensajes empáticos de respaldo si el modelo no está cargado |
| Modos con/sin memoria | Chats persistentes o modo sin memoria sin historial guardado en Vibe |
| Mensajes en tiempo real | WebSocket con reconexión automática (backoff de 1s a 30s) |
| Mensajes autodestructivos | Opción de envío efímero; el mensaje se elimina solo (mínimo 5s, máximo 5min) |
| Presencia en tiempo real | Estado online/offline con expiración automática en Redis (TTL) |
| Notificaciones por contacto | Contador individual de no leídos por cada contacto |
| Mensajería desacoplada | RabbitMQ + worker independiente con reintentos y cola de fallos |
| Autenticación JWT revocable | Tokens firmados y validados también contra Redis para invalidación inmediata |
| Locks distribuidos | Liberación atómica con script Lua en Redis durante el registro |
| Redes segmentadas | Capas pública, de aplicación y de datos siguiendo principios de OWASP |
| Trazabilidad | Un `request_id` único viaja por la API, RabbitMQ y el worker, visible en los logs |
| Observabilidad | Dozzle, Portainer, RabbitMQ Management y Redis Commander |
| CI/CD | GitHub Actions construye y publica 3 imágenes en DockerHub en cada push |
| Resiliencia de arranque | API, base de datos y broker reintentan la conexión en lugar de fallar si un servicio tarda en levantar |

---

## Requisitos

### Software

Necesitas **Docker Desktop**, que incluye Docker Engine y Docker Compose. La
instalación se explica paso a paso en la siguiente sección.

| Software | Para qué se usa |
|---|---|
| Docker Desktop | Ejecuta y orquesta todos los contenedores |
| Git | Descargar los archivos del repositorio |
| Python 3 (solo con WSL) | Generar las claves de seguridad |

### Hardware

| Recurso | Sin IA (solo chat) | Con IA (Lumi activa) |
|---|---|---|
| Procesador | 2 núcleos | 4 núcleos o más |
| Memoria RAM | 4 GB | 8 GB (16 GB recomendado) |
| Disco libre | 2 GB | 10 GB |
| Internet | Solo al instalar | Solo al instalar |

> Si tu equipo tiene poca RAM, puedes usar Vibe **sin descargar el modelo de
> IA**. En ese caso Lumi responde con mensajes empáticos predefinidos (modo
> "reposando") y el chat entre usuarios funciona con normalidad.

---

## Instalación en Windows

En Windows hay dos formas de hacerlo. Elige una:

- **Opción A — WSL (Ubuntu).** Es la recomendada. Permite usar los comandos
  cortos del Makefile (`make ...`).
- **Opción B — PowerShell.** No requiere WSL ni Python, pero usarás los
  comandos completos de Docker en lugar del Makefile.

Ambas opciones necesitan primero instalar Docker Desktop y Git.

### Paso 1 — Instalar Docker Desktop

1. Descarga el instalador desde https://www.docker.com/products/docker-desktop
2. Ejecútalo con las opciones predeterminadas.
3. Reinicia el computador cuando lo pida.
4. Abre Docker Desktop desde el menú de inicio.
5. Espera a que el ícono de la barra de tareas deje de animarse y quede estable
   (eso indica que Docker está listo).

### Paso 2 — Instalar Git

1. Descarga el instalador desde https://git-scm.com/download/win
2. Instálalo con las opciones predeterminadas.

### Paso 3 — Elegir tu terminal

**Si vas con la Opción A (WSL):** Docker Desktop ya instala WSL. Busca
**Ubuntu** en el menú de inicio y ábrelo. Si no aparece, abre **PowerShell como
administrador**, ejecuta `wsl --install`, reinicia, y vuelve a buscar Ubuntu.
Dentro de Ubuntu, instala Python, Make y Git:

```bash
sudo apt update
sudo apt install -y python3 python3-pip make git
```

**Si vas con la Opción B (PowerShell):** abre PowerShell normal. No necesitas
instalar nada más.

### Paso 4 — Descargar los archivos del proyecto

No necesitas clonar todo el repositorio: solo tres archivos.

**Opción A (Ubuntu/WSL):**
```bash
mkdir vibe-deploy && cd vibe-deploy
curl -O https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/docker-compose.prod.yml
curl -O https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/.env.example
curl -O https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/Makefile
mv .env.example .env
```

**Opción B (PowerShell):**
```powershell
mkdir vibe-deploy; cd vibe-deploy
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/docker-compose.prod.yml" -OutFile "docker-compose.prod.yml"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/.env.example" -OutFile ".env"
```

### Paso 5 — Generar las claves de seguridad

El sistema necesita dos claves secretas (`JWT_SECRET` y `WORKER_SECRET`) para
firmar las sesiones. Sin ellas la API no arranca.

**Opción A (Ubuntu/WSL):**
```bash
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(48))" >> .env
python3 -c "import secrets; print('WORKER_SECRET=' + secrets.token_urlsafe(48))" >> .env
```

**Opción B (PowerShell):** este método genera claves seguras sin los
caracteres `+`, `/` ni `=`, que romperían el archivo `.env`.
```powershell
$bytes = New-Object 'System.Byte[]' 36
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$jwt = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
Add-Content .env "JWT_SECRET=$jwt"
$rng.GetBytes($bytes)
$worker = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
Add-Content .env "WORKER_SECRET=$worker"
```

Verifica que las dos líneas quedaron al final del archivo `.env`:

```powershell
Get-Content .env -Tail 2
```

### Paso 6 — Levantar el sistema

La primera vez descarga unos 600 MB de imágenes, así que tarda entre 3 y 5
minutos.

**Opción A (Ubuntu/WSL):**
```bash
make prod-up
```

**Opción B (PowerShell):**
```powershell
docker compose -f docker-compose.prod.yml up -d
```

### Paso 7 — Abrir la aplicación

Espera unos 30 segundos (en equipos más lentos, hasta 90 segundos, mientras
RabbitMQ y la base de datos terminan de arrancar) y abre tu navegador en:

### http://localhost

Inicia sesión con cualquier correo de demo. Si el correo no existe, Vibe te
pedirá un nombre visible; si ya existe, entra directo. La IA arranca en modo
"reposando" hasta que descargues su modelo: ve a
[Activar la IA (Lumi)](#activar-la-ia-lumi).

---

## Cómo probar que funciona

### Prueba 1 — Login por correo y chat entre dos usuarios

1. Entra con el correo **alice@example.com**. Si es la primera vez, escribe el nombre visible **Alice**.
2. Abre una **ventana de incógnito** (Ctrl+Shift+N en Chrome o Edge).
3. Ve a http://localhost y entra con **bob@example.com**. Si es la primera vez, escribe **Bob**.
4. En la ventana de Alice, Bob aparece automáticamente en la lista de contactos.
5. Haz clic en Bob y escríbele un mensaje.
6. Cambia a la ventana de Bob: el mensaje aparece al instante.

Si esto funciona, el login, el WebSocket, la base de datos y las notificaciones están operando bien.

### Prueba 2 — Mensaje autodestructivo

1. Dentro de un chat, haz clic en el ícono de llama a la izquierda del campo de
   texto (se pone rojo cuando está activo).
2. Envía un mensaje. Verás un contador regresivo de 30 segundos.
3. Al llegar a cero, el mensaje desaparece de la conversación.

### Prueba 3 — Conversar con Lumi con/sin memoria

1. Lumi aparece anclada arriba en la lista de contactos, con avatar púrpura.
2. Haz clic en Lumi y escríbele algo en modo **Con memoria**.
3. Cambia a **Sin memoria** con el botón de ojo del encabezado y envía otro mensaje.
4. Cambia de vuelta a **Con memoria**: los mensajes sin memoria no deben aparecer en el historial persistente.
5. Si descargaste el modelo, Lumi responde con IA local; si no, responde con un mensaje empático de respaldo.

### Prueba 4 — Grupos públicos

1. Haz clic en **Nuevo chat** y abre la pestaña **Crear**.
2. Crea un grupo, por ejemplo **Programación**.
3. Desde otra ventana/sesión, busca el grupo en **Nuevo chat → Grupos** y únete.
4. Envía un mensaje desde una sesión: si la otra está dentro del grupo, el mensaje llega en vivo.
5. Si la otra sesión está en otro chat, aparece un badge de no leído en el grupo.
6. Los mensajes del grupo muestran el nombre visible de quien escribió.

### Prueba 5 — Chat persona-persona sin memoria

1. Haz clic en **Nuevo chat → Personas**.
2. Elegí **Sin memoria** antes de seleccionar a la persona.
3. Envía un mensaje: debe mostrarse en vivo, pero no quedar guardado al volver a abrir el chat.
4. Volvé a iniciar un chat en modo **Con memoria**: los mensajes sin memoria no deben aparecer.

### Prueba 6 — Trazabilidad (request_id)

1. Levanta las herramientas de observabilidad (ver
   [Interfaces y observabilidad](#interfaces-y-observabilidad)) y abre Dozzle en
   http://localhost:9999.
2. Haz clic en `chat_api` en la lista de la izquierda.
3. Envía un mensaje en la app.
4. Busca en los logs una línea con un código entre corchetes, por ejemplo
   `[b7d4a2e1]`.
5. Escribe ese código en el buscador de Dozzle y alterna entre `chat_api` y
   `chat_worker`: verás el mismo código en ambos, demostrando que el mensaje se
   puede rastrear a través de todo el sistema.

---

## Activar la IA (Lumi)

El contenedor de Ollama corre en una red aislada, sin acceso a internet, por
seguridad. Para descargar el modelo se conecta a internet de forma temporal,
se descarga, y se vuelve a aislar. Este procedimiento está automatizado.

El modelo pesa unos 2 GB, así que la descarga tarda entre 3 y 10 minutos. Solo
hay que hacerlo una vez: el modelo queda guardado y sobrevive a reinicios.

**Opción A (Ubuntu/WSL):**
```bash
make prod-pull-model
```

**Opción B (PowerShell):**
```powershell
$NETWORK = (docker network ls --format "{{.Name}}" | Select-String "public_network").ToString()
docker network connect $NETWORK chat_ollama
docker exec -i chat_ollama ollama pull llama3.2:3b
docker network disconnect $NETWORK chat_ollama
```

Al terminar, verifica que el modelo quedó instalado:

```powershell
docker exec chat_ollama ollama list
```

Debe aparecer `llama3.2:3b` en la lista.

---

## Interfaces y observabilidad

La aplicación y la documentación de la API están siempre disponibles:

| Interfaz | URL | Para qué sirve |
|---|---|---|
| Aplicación Vibe | http://localhost | La app principal |
| Swagger (API) | http://localhost/api/docs | Probar los endpoints desde el navegador |
| ReDoc (API) | http://localhost/api/redoc | Documentación legible de la API |

RabbitMQ Management queda disponible siempre para inspeccionar el broker:

| Herramienta | URL | Credenciales | Para qué sirve |
|---|---|---|---|
| RabbitMQ Management | http://localhost:15672 | usuario y clave del `.env` | Ver colas, conexiones y tráfico del broker |

Las demás herramientas de monitoreo están **desactivadas por defecto** y se
activan con un *profile* de Docker Compose. Para levantarlas (por ejemplo, para
la sustentación):

**Opción A (Ubuntu/WSL):** edita el comando o levanta directamente con compose.
**Ambas opciones:**
```bash
docker compose -f docker-compose.prod.yml --profile observability up -d
```

Con el profile activo también quedan disponibles:

| Herramienta | URL | Credenciales | Para qué sirve |
|---|---|---|---|
| Dozzle | http://localhost:9999 | (ninguna) | Logs de todos los contenedores en vivo |
| Redis Commander | http://localhost:8081 | (ninguna) | Explorar las claves de Redis |
| Portainer | http://localhost:9000 | se crean al primer ingreso | Administrar contenedores y volúmenes |

> Las herramientas de administración y monitoreo no deben exponerse en internet
> sin protección adicional. Están pensadas para uso local y evaluación.

---

## Endpoints de la API

La forma más cómoda de explorarlos es Swagger UI en http://localhost/api/docs.

| Método | Endpoint | Requiere token | Descripción |
|---|---|---|---|
| GET | `/` | No | Estado del sistema |
| POST | `/usuarios` | No | Registrar o reingresar un usuario (devuelve token) |
| GET | `/usuarios` | No | Listar todos los usuarios |
| GET | `/usuarios/me` | Sí | Datos del usuario autenticado |
| GET | `/usuarios/{id}/presencia` | No | Estado de conexión de un usuario |
| POST | `/usuarios/presencia/bulk` | No | Estado de conexión de varios usuarios |
| POST | `/mensaje_privado` | Sí | Enviar un mensaje privado (admite autodestrucción con `expira_en`) |
| GET | `/conversacion/{id}` | Sí | Historial de mensajes recibidos (heredado, paginado) |
| GET | `/conversacion/{id}/{contacto_id}` | Sí | Conversación entre dos usuarios (paginada) |
| GET | `/no_leidos/{id}` | Sí | Mensajes no leídos, con desglose por contacto |
| DELETE | `/no_leidos/{id}/{contacto}` | Sí | Marcar una conversación como leída |
| POST | `/ia/mensaje` | Sí | Enviar un mensaje a Lumi |
| GET | `/ia/estado` | No | Verificar si Lumi está disponible |
| POST | `/interno/notificar` | Secreto de worker | Endpoint interno usado solo por el worker |
| WS | `/ws/{usuario_id}` | Sí (primer mensaje) | Conexión WebSocket en tiempo real |

> **Sobre el WebSocket:** el token no viaja en la URL. El cliente lo envía como
> primer mensaje (`{"tipo": "auth", "token": "<JWT>"}`) dentro de los primeros
> 10 segundos; si no, la conexión se cierra. Esto evita que el token quede
> registrado en los logs de Nginx.

### Ejemplo: registrar un usuario

```bash
curl -X POST http://localhost/api/usuarios \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Alice"}'
```

La respuesta incluye el `id`, el `nombre` y el `token` JWT que se usa para las
llamadas autenticadas.

---

## Comandos del Makefile

> Los comandos `make` solo funcionan en la Opción A (Ubuntu/WSL). En PowerShell
> usa el comando completo de Docker que aparece en cada caso.

### Producción (imágenes de DockerHub)

| Comando | Equivalente en PowerShell | Qué hace |
|---|---|---|
| `make prod-up` | `docker compose -f docker-compose.prod.yml up -d` | Levanta el sistema |
| `make prod-down` | `docker compose -f docker-compose.prod.yml down` | Lo detiene (conserva datos) |
| `make prod-pull` | `docker compose -f docker-compose.prod.yml pull` | Actualiza a las últimas imágenes |
| `make prod-pull-model` | (ver [Activar la IA](#activar-la-ia-lumi)) | Descarga el modelo de IA |
| `make prod-logs` | `docker compose -f docker-compose.prod.yml logs -f` | Muestra los logs en vivo |
| `make prod-status` | `docker compose -f docker-compose.prod.yml ps` | Muestra el estado de los contenedores |

### Mantenimiento

| Comando | Qué hace |
|---|---|
| `make reset-db` | Borra mensajes y usuarios para una demo limpia (Ubuntu/WSL) |
| `make clean` | Borra TODOS los datos persistentes (pide confirmación) |
| `make disk` | Muestra el uso de disco de Docker |
| `make prune` | Limpia caché de builds antiguos sin tocar datos |

En PowerShell, para una limpieza total equivalente a `make clean`:
```powershell
docker compose -f docker-compose.prod.yml down -v
```

---

## Arquitectura

El sistema tiene 10 contenedores en 3 redes con niveles crecientes de
aislamiento:

- **public_network** — Capa accesible desde el navegador. Contiene el frontend
  (Nginx), la API y la consola RabbitMQ Management.
- **app_network** — Capa de mensajería (RabbitMQ y worker). Marcada como
  `internal`: sin salida a internet.
- **data_network** — Capa de datos (MariaDB, Redis, Ollama). También `internal`:
  totalmente aislada del exterior.

Si alguien comprometiera el frontend, no podría llegar directamente a la base de
datos: tendría que pasar por la API.

| Componente | Tecnología | Rol |
|---|---|---|
| Frontend | React + Vite + Tailwind + Nginx | Interfaz de usuario |
| API | FastAPI + Uvicorn | Servidor principal (las tres redes) |
| Base de datos | MariaDB 11 | Mensajes y usuarios |
| Caché y locks | Redis 7 | Sesiones, presencia, contadores |
| IA (Lumi) | Ollama `llama3.2:3b` | Compañera virtual |
| Broker | RabbitMQ 3.13 | Eventos asíncronos |
| Worker | Python + aio-pika | Procesa notificaciones |
| Dozzle | amir20/dozzle | Logs en vivo |
| Redis Commander | rediscommander | Explorador de Redis |
| Portainer | portainer-ce | Administrador de Docker |

### Recorrido de un mensaje

1. El usuario A envía el mensaje (`POST /mensaje_privado`).
2. La API genera un `request_id` y valida emisor y receptor.
3. La API guarda el mensaje en MariaDB (fuente de verdad).
4. La API publica un evento en RabbitMQ con el `request_id`.
5. La API responde al usuario A; el resto ocurre en segundo plano.
6. El worker consume el evento y adopta el mismo `request_id`.
7. El worker llama al endpoint interno de la API.
8. La API incrementa el contador de no leídos en Redis.
9. La API notifica al usuario B por WebSocket si está conectado.

Cada paso deja un log con el mismo `request_id`, lo que permite rastrear el
recorrido completo en Dozzle.

---

## CI/CD

Cada `push` a la rama `main` dispara un pipeline en **GitHub Actions** que:

1. Ejecuta las pruebas con pytest.
2. Construye las tres imágenes en paralelo (API, worker, frontend).
3. Las publica en DockerHub con dos etiquetas: `latest` y el SHA del commit (para
   poder volver a una versión anterior).

Las imágenes están en https://hub.docker.com/u/crisdatap

- `crisdatap/vibe-api`
- `crisdatap/vibe-worker`
- `crisdatap/vibe-frontend`

---

## Solución de problemas

### Al registrarme aparece "Unexpected token '<'... is not valid JSON"

La API todavía no está lista detrás de Nginx (suele pasar los primeros segundos,
o si la API está reiniciándose). Espera hasta 90 segundos y recarga. Si persiste,
revisa los logs de la API:

```powershell
docker logs chat_api --tail 30
```

Debe terminar con la línea "API lista para recibir solicitudes".

### La API se reinicia en bucle con "Access denied for user 'chat_user'"

MariaDB guarda las credenciales en su volumen de datos **solo en el primer
arranque**. Si cambiaste el `.env` después, o si tenía caracteres con tilde,
las credenciales quedan desfasadas. La solución es borrar el volumen y volver a
arrancar desde cero (es seguro en una instalación nueva, sin datos que perder):

```powershell
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

### El arranque falla con "dependency rabbitmq failed to start ... is unhealthy"

En equipos lentos, RabbitMQ puede tardar más de lo normal en arrancar (40
segundos o más) y la API/worker, que dependen de él, no esperan lo suficiente.
El sistema ya está configurado para darle hasta 90 segundos. Si aun así falla,
reinicia desde cero:

```powershell
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

Luego espera 90 segundos y verifica el estado:

```powershell
docker compose -f docker-compose.prod.yml ps
```

### La API se reinicia en bucle con un error sobre JWT_SECRET o WORKER_SECRET

Faltan las claves de seguridad en el `.env`. Revisa que estén:

```powershell
Get-Content .env -Tail 2
```

Si no aparecen, vuelve al [Paso 5](#paso-5--generar-las-claves-de-seguridad)
para generarlas y luego reinicia la API:

```powershell
docker compose -f docker-compose.prod.yml restart api
```

### Lumi responde "Estoy descansando..." en lugar de con IA

El modelo no está descargado. Es el comportamiento esperado si saltaste el paso
de [Activar la IA](#activar-la-ia-lumi). Descárgalo y vuelve a intentar.

### Lumi tarda mucho en responder (más de un minuto)

Es normal la primera vez después de arrancar: el modelo tarda de 30 a 60
segundos en cargar en memoria. Las respuestas siguientes son más rápidas (de 3
a 15 segundos). Si tu equipo tiene GPU, Ollama la usa automáticamente.

### "Cannot connect to the Docker daemon"

Docker Desktop no está corriendo. Ábrelo desde el menú de inicio, espera a que
el ícono quede estable, y reintenta.

### "Bind for 0.0.0.0:XXXX failed: port is already allocated"

Otro proceso (o un contenedor viejo) está usando ese puerto. Revisa y elimina
contenedores anteriores:

```powershell
docker ps -a
docker rm -f <nombre-del-contenedor-viejo>
```

### El frontend muestra una versión vieja después de actualizar

Es la caché del navegador. Actualiza las imágenes y fuerza la recreación:

```powershell
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

También puedes recargar con Ctrl+Shift+R.

---

## Estructura del proyecto

```
proyecto-chat-distribuido/
├── app/                        # Backend Python (FastAPI)
│   ├── main.py                 # Punto de entrada, ciclo de vida y middleware
│   ├── auth.py                 # Autenticación JWT y secreto del worker
│   ├── models.py               # Modelos de datos (Pydantic)
│   ├── database.py             # Pool de conexiones MariaDB y tablas
│   ├── cache.py                # Redis: caché, locks, presencia, sesiones
│   ├── queue.py                # Conexión a RabbitMQ y publicación de eventos
│   ├── worker.py               # Proceso que consume la cola y notifica
│   ├── request_id.py           # Identificador de trazabilidad por petición
│   ├── logging_config.py       # Configuración central de logs
│   └── routers/                # Endpoints de la API
│       ├── usuarios.py         # Registro, listado y presencia
│       ├── mensajes.py         # Mensajes privados y conversaciones
│       ├── ia.py               # Lumi (envío y estado)
│       ├── websocket.py        # Conexiones en tiempo real
│       └── interno.py          # Endpoint interno usado por el worker
├── frontend/                   # Frontend React
│   ├── src/
│   │   ├── components/         # Componentes de interfaz
│   │   ├── services/           # Cliente HTTP y WebSocket
│   │   ├── hooks/              # Hooks personalizados (presencia)
│   │   ├── utils/              # Utilidades (colores de avatar, tiempo)
│   │   ├── App.jsx             # Componente raíz
│   │   └── main.jsx            # Punto de entrada de React
│   ├── Dockerfile              # Build en dos etapas: Node y luego Nginx
│   └── nginx.conf              # Proxy de /api y /ws, y servido de la SPA
├── tests/                      # Pruebas con pytest
├── .github/workflows/
│   └── docker.yml              # Pipeline de CI/CD en GitHub Actions
├── docker-compose.yml          # Orquestación para desarrollo (build local)
├── docker-compose.prod.yml     # Orquestación para producción (DockerHub)
├── Dockerfile                  # Imagen del backend
├── Dockerfile.worker           # Imagen del worker
├── Makefile                    # Atajos de operación
├── requirements.txt            # Dependencias de Python
├── .env.example                # Plantilla de variables de entorno
└── README.md                   # Este archivo
```

---

## Instalación para desarrollo

Esta sección solo aplica si quieres **modificar el código fuente**. Si solo
quieres ejecutar Vibe, usa la [instalación normal](#instalación-en-windows).

A diferencia de la instalación con imágenes de DockerHub, aquí se clona el
repositorio completo y se construyen las imágenes localmente desde el código.

```bash
git clone https://github.com/crisdata/proyecto-chat-distribuido.git
cd proyecto-chat-distribuido
cp .env.example .env

# Generar las dos claves de seguridad
echo "JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" >> .env
echo "WORKER_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" >> .env

# Construir y levantar (la primera vez tarda de 5 a 10 minutos)
make up

# Descargar el modelo de IA
make pull-model
```

La aplicación queda en http://localhost. Después de modificar código:

```bash
# Backend (carpeta app/)
docker compose up --build -d api worker

# Frontend (carpeta frontend/)
docker compose build --no-cache frontend
docker compose up -d --force-recreate frontend
```

---

## Licencia

Proyecto de uso académico desarrollado para el programa de Ingeniería de
Sistemas de COTECNOVA. El código está disponible públicamente con fines
educativos.
