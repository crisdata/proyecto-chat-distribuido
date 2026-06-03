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

1. [Ruta rápida para instalar](#ruta-rápida-para-instalar)
2. [Qué es Vibe](#qué-es-vibe)
3. [Qué incluye el sistema](#qué-incluye-el-sistema)
4. [Requisitos](#requisitos)
5. [Instalación en Windows](#instalación-en-windows)
6. [Cómo probar que funciona](#cómo-probar-que-funciona)
7. [Activar la IA (Lumi)](#activar-la-ia-lumi)
8. [Interfaces y observabilidad](#interfaces-y-observabilidad)
9. [Endpoints de la API](#endpoints-de-la-api)
10. [Comandos del Makefile](#comandos-del-makefile)
11. [Arquitectura](#arquitectura)
12. [CI/CD](#cicd)
13. [Solución de problemas](#solución-de-problemas)
14. [Estructura del proyecto](#estructura-del-proyecto)
15. [Instalación para desarrollo](#instalación-para-desarrollo)

---

## Ruta rápida para instalar

Si solo quieres poner Vibe a funcionar en Windows, sigue este camino:

1. Instala **Docker Desktop**.
2. Abre **PowerShell**.
3. Descarga `docker-compose.prod.yml` y `.env.example` (renómbralo a `.env`).
4. Reemplaza `JWT_SECRET` y `WORKER_SECRET` en el `.env`.
5. Ejecuta:
   ```powershell
   docker compose -f docker-compose.prod.yml up -d
   ```
6. Espera entre 30 y 90 segundos.
7. Abre http://localhost.

Si ves la pantalla de login de Vibe, la instalación básica quedó lista.

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
| Notificaciones | Contadores de no leídos por contacto y por grupo |
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

| Software | Obligatorio | Para qué se usa |
|---|---|---|
| Docker Desktop | Sí | Ejecuta y orquesta todos los contenedores |
| PowerShell | Sí en Windows | Descargar archivos y ejecutar Docker; ya viene instalado en Windows |
| Git | No para ejecutar; sí para desarrollo | Clonar el repositorio completo si quieres modificar código |
| Python 3 | Solo con WSL/desarrollo | Generar claves y trabajar con el backend |

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

- **Opción A — PowerShell.** Es la más simple si solo quieres ejecutar la app.
  No requiere WSL ni Python.
- **Opción B — WSL (Ubuntu).** Es cómoda si ya usas Linux o quieres usar los
  comandos cortos del Makefile (`make ...`).

Ambas opciones necesitan Docker Desktop. Git solo es necesario si quieres clonar el repositorio completo o modificar código.

### Paso 1 — Instalar Docker Desktop

1. Descarga el instalador desde https://www.docker.com/products/docker-desktop
2. Ejecútalo con las opciones predeterminadas.
3. Reinicia el computador cuando lo pida.
4. Abre Docker Desktop desde el menú de inicio.
5. Espera a que el ícono de la barra de tareas deje de animarse y quede estable
   (eso indica que Docker está listo).

### Paso 2 — Instalar Git (opcional)

Para ejecutar Vibe con Docker no necesitas Git. Puedes saltar este paso.

Instala Git solo si quieres clonar el repositorio completo o modificar código:

1. Descarga el instalador desde https://git-scm.com/download/win
2. Instálalo con las opciones predeterminadas.

### Paso 3 — Elegir tu terminal

**Si vas con PowerShell:** abre PowerShell normal. No necesitas instalar nada
más.

**Si vas con WSL (Ubuntu):**

1. Abre Docker Desktop.
2. Ve a **Settings** (ícono de engranaje) -> **Resources** -> **WSL Integration**.
3. Activa **Enable integration with my default WSL distro**.
4. Si aparece **Ubuntu**, activa también su interruptor.
5. Pulsa **Apply & restart**.
6. Abre **Ubuntu** desde el menú de inicio.
7. Dentro de Ubuntu, instala Python, Make y Git:

```bash
sudo apt update
sudo apt install -y python3 python3-pip make git
```

> Si no ves Ubuntu, usa PowerShell o instala Ubuntu desde Microsoft Store.

### Paso 4 — Descargar los archivos del proyecto

No necesitas clonar todo el repositorio: solo debes descargar los archivos de arranque.

**PowerShell:**
```powershell
mkdir vibe-deploy; cd vibe-deploy
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/docker-compose.prod.yml" -OutFile "docker-compose.prod.yml"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/.env.example" -OutFile ".env"
```

**WSL / Ubuntu:**
```bash
mkdir vibe-deploy && cd vibe-deploy
curl -L -o docker-compose.prod.yml https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/docker-compose.prod.yml
curl -L -o .env https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/.env.example
curl -L -o Makefile https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/Makefile
```

Al terminar, verifica que tienes estos archivos:

```text
.env
docker-compose.prod.yml
Makefile        # solo si usaste WSL/Ubuntu
```

### Paso 5 — Generar las claves de seguridad

El archivo `.env` ya trae dos claves de ejemplo (`JWT_SECRET` y
`WORKER_SECRET`) con un valor temporal que **debes reemplazar** por valores
aleatorios. La API arranca incluso con los valores de ejemplo, pero es
inseguro: cualquiera que conozca esas claves podría firmar tokens falsos.
Solo falla si las claves faltan o están vacías.

**PowerShell:** genera claves sin los caracteres `+`, `/` ni `=` y reemplaza las líneas existentes sin duplicarlas.
```powershell
function New-Clave {
  $bytes = New-Object 'System.Byte[]' 36
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
}
$jwt = New-Clave
$worker = New-Clave
(Get-Content .env) `
  -replace '^JWT_SECRET=.*', "JWT_SECRET=$jwt" `
  -replace '^WORKER_SECRET=.*', "WORKER_SECRET=$worker" |
  Set-Content -Path .env -Encoding ascii
```

Verifica que las dos claves quedaron con valores nuevos y que no están duplicadas:

```powershell
Select-String -Path .env -Pattern "JWT_SECRET|WORKER_SECRET"
```

**WSL / Ubuntu:**
```bash
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')|" .env
sed -i "s|^WORKER_SECRET=.*|WORKER_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')|" .env

grep -E 'JWT_SECRET|WORKER_SECRET' .env
```

### Paso 6 — Levantar el sistema

La primera vez descarga unos 600 MB de imágenes, así que tarda entre 3 y 5
minutos.

**PowerShell:**
```powershell
docker compose -f docker-compose.prod.yml up -d
```

**WSL / Ubuntu:**
```bash
make prod-up
```

Comprueba que los contenedores arrancaron:

```powershell
docker compose -f docker-compose.prod.yml ps
```

Algunos servicios pueden aparecer como `starting` durante los primeros segundos. Espera hasta 90 segundos antes de abrir la app.

### Paso 7 — Abrir la aplicación

Espera unos 30 segundos. En equipos lentos puede tardar hasta 90 segundos, mientras RabbitMQ y la base de datos terminan de arrancar.

Luego abre:

```text
http://localhost
```

Inicia sesión con cualquier correo de demo. Si el correo no existe, Vibe te pedirá un nombre visible; si ya existe, entra directo.

La IA arranca en modo "reposando" hasta que descargues su modelo. Si quieres activar respuestas generadas por IA local, ve a [Activar la IA (Lumi)](#activar-la-ia-lumi).

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
3. Desde otra ventana/sesión, busca el grupo en **Nuevo chat -> Grupos** y únete.
4. Envía un mensaje desde una sesión: si la otra está dentro del grupo, el mensaje llega en vivo.
5. Si la otra sesión está en otro chat, aparece un badge de no leído en el grupo.
6. Los mensajes del grupo muestran el nombre visible de quien escribió.

### Prueba 5 — Chat persona-persona sin memoria

1. Haz clic en **Nuevo chat -> Personas**.
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

**PowerShell:**
```powershell
$NETWORK = docker network ls --format "{{.Name}}" | Where-Object { $_ -like "*public_network*" } | Select-Object -First 1
if (-not $NETWORK) { Write-Host "Primero levanta el sistema con docker compose up -d"; exit 1 }
docker network connect $NETWORK chat_ollama
docker exec -i chat_ollama ollama pull llama3.2:3b
docker network disconnect $NETWORK chat_ollama
```

**WSL / Ubuntu:**
```bash
make prod-pull-model
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

Para activar esas herramientas, ejecuta:

```powershell
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
| POST | `/usuarios/login` | No | Login demo por correo; si el email es nuevo puede pedir nombre visible |
| POST | `/usuarios` | No | Registro heredado por nombre; se conserva por compatibilidad |
| GET | `/usuarios` | No | Listar usuarios visibles para iniciar chats |
| GET | `/usuarios/me` | Sí | Datos del usuario autenticado |
| GET | `/usuarios/{id}/presencia` | No | Estado de conexión de un usuario |
| POST | `/usuarios/presencia/bulk` | No | Estado de conexión de varios usuarios |
| POST | `/mensaje_privado` | Sí | Enviar mensaje privado persistente; admite autodestrucción con `expira_en` |
| POST | `/mensaje_privado/sin_memoria` | Sí | Enviar mensaje privado solo en vivo, sin guardar historial |
| GET | `/conversacion/{id}/{contacto_id}` | Sí | Conversación entre dos usuarios, paginada |
| GET | `/no_leidos/{id}` | Sí | Mensajes no leídos, con desglose por contacto |
| DELETE | `/no_leidos/{id}/{contacto}` | Sí | Marcar una conversación como leída |
| POST | `/grupos` | Sí | Crear grupo público |
| GET | `/grupos/buscar` | Sí | Buscar grupos públicos por nombre |
| GET | `/grupos/mios` | Sí | Listar grupos a los que pertenece el usuario |
| POST | `/grupos/{grupo_id}/unirse` | Sí | Unirse a un grupo público |
| GET | `/grupos/{grupo_id}/mensajes` | Sí | Leer mensajes de un grupo |
| POST | `/grupos/{grupo_id}/mensajes` | Sí | Enviar mensaje a un grupo |
| POST | `/ia/mensaje` | Sí | Enviar mensaje persistente a Lumi |
| POST | `/ia/mensaje/modo` | Sí | Enviar mensaje a Lumi indicando `con_memoria` o `sin_memoria` |
| GET | `/ia/estado` | No | Verificar si Lumi está disponible |
| POST | `/interno/notificar` | Secreto de worker | Endpoint interno usado solo por el worker |
| WS | `/ws/{usuario_id}` | Sí (primer mensaje) | Conexión WebSocket en tiempo real |

> **Sobre el WebSocket:** el token no viaja en la URL. El cliente lo envía como
> primer mensaje (`{"tipo": "auth", "token": "<JWT>"}`) dentro de los primeros
> 10 segundos; si no, la conexión se cierra. Esto evita que el token quede
> registrado en los logs de Nginx.

### Ejemplo: iniciar sesión por correo

El siguiente ejemplo usa Bash (funciona en WSL, Ubuntu o Git Bash).

Primer intento con un correo nuevo:

```bash
curl -X POST http://localhost/api/usuarios/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com"}'
```

Si el correo no existe, la API responde que requiere nombre. Entonces repite el
login incluyendo `nombre`:

```bash
curl -X POST http://localhost/api/usuarios/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "nombre": "Alice"}'
```

La respuesta incluye `id`, `nombre` y `token`. No incluye el email.

---

## Comandos del Makefile

> Los comandos `make` solo funcionan en WSL/Ubuntu. En PowerShell usa el
> comando completo de Docker que aparece en cada caso.

### Producción (imágenes de DockerHub)

| Comando | Equivalente en PowerShell | Qué hace |
|---|---|---|
| `make prod-up` | `docker compose -f docker-compose.prod.yml up -d` | Levanta el sistema |
| `make prod-down` | `docker compose -f docker-compose.prod.yml down` | Lo detiene (conserva datos) |
| `make prod-pull` | `docker compose -f docker-compose.prod.yml pull` | Actualiza a las últimas imágenes |
| `make prod-pull-model` | (ver [Activar la IA](#activar-la-ia-lumi)) | Descarga el modelo de IA |
| `make prod-logs` | `docker compose -f docker-compose.prod.yml logs -f` | Muestra los logs en vivo |
| `make prod-status` | `docker compose -f docker-compose.prod.yml ps` | Muestra el estado de los contenedores |

### Mantenimiento (solo desarrollo o clon completo)

Estos comandos usan `docker-compose.yml` local y requieren tener el repositorio
completo. No funcionan si solo descargaste los archivos de producción.

| Comando | Qué hace |
|---|---|
| `make reset-db` | Limpieza básica heredada de usuarios/mensajes; para reset completo usa `make clean` |
| `make clean` | Borra TODOS los datos persistentes: usuarios, grupos, mensajes, modelo IA y volúmenes (pide confirmación) |
| `make disk` | Muestra el uso de disco de Docker |
| `make prune` | Limpia caché de builds antiguos sin tocar datos |

En PowerShell, para una limpieza total equivalente a `make clean`:

```powershell
docker compose -f docker-compose.prod.yml down -v
```

Después de una limpieza total, vuelve a levantar el sistema con:

```powershell
docker compose -f docker-compose.prod.yml up -d
```

---

## Arquitectura

El sistema define 10 servicios: 7 se levantan por defecto y 3 son opcionales
para observabilidad. Todos se organizan en 3 redes con niveles crecientes de
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

### Al iniciar sesión aparece "Unexpected token '<'... is not valid JSON"

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

Las claves de seguridad del `.env` faltan, siguen con el valor de ejemplo o
quedaron duplicadas. Revisa cómo están:

```powershell
Select-String -Path .env -Pattern "JWT_SECRET|WORKER_SECRET"
```

Si ves el valor de ejemplo (`cambia_esta_clave...`), o la misma clave aparece
dos veces, vuelve al [Paso 5](#paso-5--generar-las-claves-de-seguridad) para
regenerarlas correctamente (ese paso las reemplaza sin duplicar). Luego
reinicia la API:

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
│       ├── usuarios.py         # Login por correo, registro, listado y presencia
│       ├── mensajes.py         # Mensajes privados y conversaciones
│       ├── grupos.py           # Creación, búsqueda y chat de grupos públicos
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

# Reemplazar las dos claves de ejemplo por valores aleatorios
# (reemplaza las líneas existentes, no las duplica)
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')|" .env
sed -i "s|^WORKER_SECRET=.*|WORKER_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')|" .env

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