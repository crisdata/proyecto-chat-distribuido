# Vibe — Chat universitario con privacidad real

> Un chat que corre **completo en tu computador**. Nada sale a internet.
> Incluye a **Lumi**, una compañera virtual con inteligencia artificial local.

**Autores:** Cristian Giraldo & Sebastián Pérez
**Curso:** Programación Distribuida
**Repositorio:** https://github.com/crisdata/proyecto-chat-distribuido

[![Build Status](https://github.com/crisdata/proyecto-chat-distribuido/actions/workflows/docker.yml/badge.svg)](https://github.com/crisdata/proyecto-chat-distribuido/actions)

---

## Contenido

### 🟢 Para usar Vibe

1. [Lo único que necesitas](#lo-único-que-necesitas)
2. [Guía de instalación — 5 pasos](#guía-de-instalación-5-pasos)
3. [Recorrido guiado en 5 minutos](#recorrido-guiado-en-5-minutos)
4. [Activar a Lumi (opcional)](#activar-a-lumi-opcional)
5. [¿Algo falló?](#algo-falló)

### 🟡 Para conocer el sistema

6. [Qué es Vibe](#qué-es-vibe)
7. [Todo lo que incluye](#todo-lo-que-incluye)
8. [Cómo está construido](#cómo-está-construido)
9. [Herramientas de observabilidad](#herramientas-de-observabilidad)
10. [CI/CD](#ci-cd)

### 🔵 Para desarrollar

11. [Endpoints de la API](#endpoints-de-la-api)
12. [Comandos del Makefile](#comandos-del-makefile)
13. [Estructura del proyecto](#estructura-del-proyecto)
14. [Instalación para desarrollo](#instalación-para-desarrollo)
15. [Camino alternativo con WSL / Ubuntu](#camino-alternativo-con-wsl-ubuntu)

---

## 🟢 Lo único que necesitas

| Qué | ¿Obligatorio? | Para qué |
|-----|:---:|---|
| **Docker Desktop** | Sí | Ejecuta todo el sistema (base de datos, chat, IA...) |
| **PowerShell** | Sí | Ya viene en Windows. Escribirás los comandos ahí |
| Git | No | Solo si quieres modificar código |
| Python | No | Solo si usas WSL o vas a desarrollar |

### ¿Mi computador lo corre?

| Recurso | Sin la IA de Lumi | Con Lumi (recomendado) |
|---|---|---|
| Procesador | 2 núcleos | 4 núcleos o más |
| Memoria RAM | 4 GB | 8 GB (16 GB ideal) |
| Espacio libre | 2 GB | 10 GB |
| Internet | Solo al instalar | Solo al instalar |

> Si tienes poca RAM puedes usar Vibe sin la IA. Lumi responde con mensajes
> amigables predefinidos y el chat entre personas funciona normal.

---

## 🟢 Guía de instalación — 5 pasos

Cada paso tiene un bloque de comandos. **Cópialos, pégalos en PowerShell,
presiona Enter.** Uno por uno, en orden.

---

### Paso 1 — Instalar Docker Desktop

1. Entra a https://www.docker.com/products/docker-desktop
2. Baja el instalador y ábrelo. Deja las opciones que vienen marcadas.
3. Reinicia el computador.
4. Abre **Docker Desktop** desde el menú de inicio.
5. Espera hasta que el ícono en la barra de tareas deje de moverse.

---

### Paso 2 — Descargar los archivos de Vibe

Copia y pégalo **completo** en PowerShell:

```powershell
mkdir vibe-deploy; cd vibe-deploy
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/docker-compose.prod.yml" -OutFile "docker-compose.prod.yml"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/.env.example" -OutFile ".env"
```

> Esto crea una carpeta `vibe-deploy` y descarga dos archivos. No necesitas
> clonar nada ni instalar Git.

---

### Paso 3 — Crear las claves de seguridad

Copia y pégalo **completo** en PowerShell:

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

Verifica que funcionó:

```powershell
Select-String -Path .env -Pattern "JWT_SECRET|WORKER_SECRET"
```

Debes ver dos líneas con valores largos aleatorios (no el texto `cambia_esta_clave`).

> **¿Qué hace esto?** Genera dos contraseñas secretas para que el sistema sea
> seguro. Sin esto igual arranca, pero cualquiera podría falsificar sesiones.
> Con dos comandos queda protegido.

---

### Paso 4 — Levantar el sistema

Copia y pégalo en PowerShell:

```powershell
docker compose -f docker-compose.prod.yml up -d
```

La primera vez **descarga unos 600 MB** (tarda entre 3 y 5 minutos).
Las veces siguientes arranca en segundos.

Verifica que todo esté corriendo:

```powershell
docker compose -f docker-compose.prod.yml ps
```

Debes ver 7 servicios con estado `Up` o `healthy`. Si alguno dice `starting`,
espera un minuto y vuelve a verificar.

---

### Paso 5 — Abrir la aplicación

Espera 30 segundos (hasta 90 en computadores con pocos recursos). Luego abre tu navegador
en:

```text
http://localhost
```

Inicia sesión con **cualquier correo** de prueba. Si es la primera vez que ese
correo entra, Vibe te pide un nombre visible. Si ya existe, entras directo.

> **¿No abre?** Vuelve a ejecutar `docker compose -f docker-compose.prod.yml ps`
> y fíjate que los 7 servicios estén en verde. Si hay alguno en rojo,
> [¿Algo falló?](#algo-falló).

---

## 🟢 Recorrido guiado en 5 minutos

### Prueba 1 — Chat entre dos personas

1. Entra con el correo **alice@example.com**. Si te pide nombre, pon **Alice**.
2. Abre una **ventana de incógnito** (Ctrl+Shift+N).
3. Ve a http://localhost y entra con **bob@example.com** (nombre: **Bob**).
4. En la ventana de Alice, Bob aparece solo en la lista de contactos.
5. Clic en Bob, escribe un mensaje.
6. En la ventana de Bob: el mensaje aparece al instante.

> **Si ves esto**, el chat entre personas, las notificaciones y la base de
> datos funcionan correctamente.

### Prueba 2 — Mensaje que se autodestruye

1. Dentro de cualquier chat, clic en el ícono de llama 🔥 (se pone rojo).
2. Envía un mensaje. Aparece un contador de 30 segundos.
3. Cuando llega a cero, el mensaje desaparece solo.

### Prueba 3 — Grupos públicos

1. Clic en **Nuevo chat** → pestaña **Crear**.
2. Escribe un nombre (ej: "Programación") y crea el grupo.
3. Desde la otra ventana (Bob), ve a **Nuevo chat → Grupos**, busca el grupo
   y únete.
4. Alice escribe en el grupo. Bob lo ve al instante si está dentro del grupo.
5. Si Bob está en otro chat, aparece un numerito rojo de no leído en el grupo.
6. Los mensajes muestran el nombre de quién los escribió.

### Prueba 4 — Chatear con Lumi

1. Lumi está anclada arriba en la lista de contactos (avatar violeta).
2. Escríbele algo. Responde con mensajes empáticos aunque no hayas descargado
   el modelo de IA.

### Prueba 5 — Modo sin memoria

1. En el chat con Lumi, clic en el ojo 👁 del encabezado. Cambia a 🚫 **Sin memoria**.
2. Envía mensajes. Se ven en vivo pero **no se guardan**.
3. Vuelve a **Con memoria**: los mensajes sin memoria ya no aparecen.

### Prueba 6 — Trazabilidad

1. Activa las herramientas de [observabilidad](#herramientas-de-observabilidad).
2. Abre Dozzle en http://localhost:9999, clic en `chat_api`.
3. Envía un mensaje en la app.
4. Busca en los logs un código entre corchetes (ej: `[b7d4a2e1]`).
5. Escribe ese código en el buscador y alterna entre `chat_api` y `chat_worker`:
   el mismo código aparece en ambos. El mensaje se rastreó de punta a punta.

---

## 🟢 Activar a Lumi (opcional)

Lumi usa un modelo de IA de ~2 GB. Hay que descargarlo una sola vez. La
descarga tarda entre 3 y 10 minutos.

Asegúrate de que el sistema esté corriendo (`docker compose -f docker-compose.prod.yml ps`).

Copia y pégalo en PowerShell:

```powershell
$NETWORK = docker network ls --format "{{.Name}}" | Where-Object { $_ -like "*public_network*" } | Select-Object -First 1
if (-not $NETWORK) { Write-Host "Primero levanta el sistema con docker compose up -d"; exit 1 }
docker network connect $NETWORK chat_ollama
docker exec -i chat_ollama ollama pull llama3.2:3b
docker network disconnect $NETWORK chat_ollama
```

Verifica que el modelo quedó instalado:

```powershell
docker exec chat_ollama ollama list
```

Debe aparecer `llama3.2:3b` en la lista.

> La primera respuesta después de descargar puede tardar hasta 60 segundos
> mientras el modelo carga en memoria. Después responde en segundos.

---

## 🟢 ¿Algo falló?

### "Unexpected token '<'... is not valid JSON" al iniciar sesión

La API todavía está arrancando. Espera hasta 90 segundos y recarga la página.
Si persiste, revisa los logs:

```powershell
docker logs chat_api --tail 30
```

La última línea debe decir "API lista para recibir solicitudes".

### Error "Access denied for user 'chat_user'"

Las credenciales de la base de datos quedaron desfasadas (pasa si cambiaste el
`.env` después del primer arranque). Borra todo y vuelve a empezar:

```powershell
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

### Error "dependency rabbitmq failed to start ... is unhealthy"

En equipos lentos RabbitMQ puede tardar más de lo normal. El sistema espera hasta
90 segundos. Si igual falla:

```powershell
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

Espera 90 segundos y verifica con `docker compose -f docker-compose.prod.yml ps`.

### Error sobre JWT_SECRET o WORKER_SECRET

Las claves no se generaron bien o quedaron duplicadas. Revisa:

```powershell
Select-String -Path .env -Pattern "JWT_SECRET|WORKER_SECRET"
```

Si ves `cambia_esta_clave` o la misma clave repetida, vuelve al
[Paso 3](#paso-3-crear-las-claves-de-seguridad) y ejecútalo de nuevo.
Luego:

```powershell
docker compose -f docker-compose.prod.yml restart api
```

### Lumi responde "Estoy descansando..."

Normal: no descargaste el modelo de IA. Ve a
[Activar a Lumi](#activar-a-lumi-opcional).

### Lumi tarda más de un minuto en responder

Normal la primera vez después de arrancar: el modelo carga en memoria. Las
siguientes respuestas tardan entre 3 y 15 segundos.

### "Cannot connect to the Docker daemon"

Docker Desktop no está corriendo. Ábrelo desde el menú de inicio, espera a que
el ícono se estabilice, y vuelve a intentar.

### "port is already allocated"

Hay otro programa usando el mismo puerto. Busca contenedores viejos y
elimínalos:

```powershell
docker ps -a
docker rm -f <nombre-del-contenedor>
```

### El frontend se ve viejo después de actualizar

El navegador guardó una copia en caché. Actualiza imágenes y fuerza recreación:

```powershell
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

También puedes recargar con Ctrl+Shift+R.

### Limpiar todo y volver a empezar

```powershell
docker compose -f docker-compose.prod.yml down -v
```

Esto borra chats, usuarios, grupos y el modelo de IA. Después vuelve a
levantar con:

```powershell
docker compose -f docker-compose.prod.yml up -d
```

---

## 🟡 Qué es Vibe

Vibe es una aplicación de chat donde varios usuarios conversan entre sí
mediante mensajes privados en tiempo real. Incluye a **Lumi**, una compañera
virtual basada en un modelo de IA que corre localmente con Ollama: **ningún
mensaje sale hacia servicios externos**.

El sistema se compone de **10 contenedores Docker** repartidos en **3 redes
aisladas** con distintos niveles de seguridad. Internamente usa mensajería
asíncrona, caché, autenticación JWT y observabilidad.

---

## 🟡 Todo lo que incluye

| Funcionalidad | Cómo funciona |
|---|---|
| Login por correo | Demo con email normalizado y nombre visible. El email nunca se muestra en la interfaz, la API ni el token |
| Chat privado entre personas | Mensajes guardados en base de datos, autenticación JWT |
| Grupos públicos | Cualquiera puede crear, buscar y unirse. Sin administradores ni moderación |
| Compañera virtual Lumi | Modelo `llama3.2:3b` con Ollama en red aislada. Si el modelo no está, responde con mensajes empáticos |
| Modos con y sin memoria | Chat persistente o modo efímero sin historial guardado |
| Mensajes en tiempo real | WebSocket con reconexión automática |
| Mensajes autodestructivos | Se eliminan solos después de 30 segundos |
| Presencia en tiempo real | Estado online/offline con expiración automática |
| Notificaciones | Contadores de no leídos por persona y por grupo |
| Mensajería desacoplada | RabbitMQ + worker independiente con reintentos |
| Autenticación revocable | Tokens JWT validados también contra Redis |
| Locks distribuidos | Registro atómico con script Lua en Redis |
| Redes segmentadas | 3 capas de red con aislamiento progresivo |
| Trazabilidad | Un `request_id` único viaja por API, RabbitMQ y worker |
| Observabilidad | Dozzle, Portainer, RabbitMQ Management y Redis Commander |
| CI/CD | GitHub Actions publica imágenes en DockerHub en cada push |
| Resiliencia | API, base de datos y broker reintentan conexión en lugar de fallar |

---

## 🟡 Cómo está construido

El sistema define **10 servicios**: 7 se levantan por defecto, 3 son
opcionales para observabilidad. Todos viven en 3 redes:

- **public_network** — Accesible desde el navegador: frontend (Nginx), API y
  consola RabbitMQ.
- **app_network** — Mensajería interna: RabbitMQ y worker. Sin salida a internet.
- **data_network** — Datos: MariaDB, Redis, Ollama. Totalmente aislada.

| Componente | Tecnología | Rol |
|---|---|---|
| Frontend | React + Vite + Tailwind + Nginx | Interfaz de usuario |
| API | FastAPI + Uvicorn | Servidor principal |
| Base de datos | MariaDB 11 | Mensajes y usuarios |
| Caché | Redis 7 | Sesiones, presencia, locks |
| IA (Lumi) | Ollama `llama3.2:3b` | Compañera virtual |
| Broker | RabbitMQ 3.13 | Mensajería asíncrona |
| Worker | Python + aio-pika | Procesa notificaciones |
| Dozzle | amir20/dozzle | Logs en vivo (opcional) |
| Redis Commander | rediscommander | Explorador Redis (opcional) |
| Portainer | portainer-ce | Gestor Docker (opcional) |

### ¿Cómo viaja un mensaje?

1. Remitente envía (`POST /mensaje_privado`).
2. API genera `request_id`, valida y guarda en MariaDB.
3. API publica evento en RabbitMQ con el mismo `request_id`.
4. Worker consume el evento, adopta el `request_id`.
5. Worker notifica a la API internamente.
6. API incrementa contador de no leídos en Redis.
7. API avisa al destinatario por WebSocket si está conectado.

Cada paso deja un log con el mismo `request_id`. En Dozzle se puede seguir el
recorrido completo.

---

## 🟡 Herramientas de observabilidad

Siempre disponibles:

| Herramienta | URL | ¿Para qué? |
|---|---|---|
| App Vibe | http://localhost | La aplicación |
| Swagger API | http://localhost/api/docs | Probar endpoints desde el navegador |
| ReDoc API | http://localhost/api/redoc | Documentación legible de la API |
| RabbitMQ | http://localhost:15672 | Ver colas y tráfico (usuario y clave en `.env`) |

Herramientas **opcionales** (activar con un comando extra):

```powershell
docker compose -f docker-compose.prod.yml --profile observability up -d
```

| Herramienta | URL | Para qué |
|---|---|---|
| Dozzle | http://localhost:9999 | Logs en vivo de todos los contenedores |
| Redis Commander | http://localhost:8081 | Explorar claves de Redis |
| Portainer | http://localhost:9000 | Gestionar contenedores (crea usuario al entrar) |

---

## 🟡 CI/CD

Cada `push` a `main` dispara un pipeline en GitHub Actions que:

1. Corre las pruebas con pytest.
2. Construye 3 imágenes en paralelo (API, worker, frontend).
3. Publica en DockerHub con etiquetas `latest` y el SHA del commit.

Imágenes: https://hub.docker.com/u/crisdatap

---

## 🔵 Endpoints de la API

Explóralos visualmente en http://localhost/api/docs (Swagger UI).

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/` | Estado del sistema |
| POST | `/usuarios/login` | Iniciar sesión por correo |
| POST | `/usuarios` | Registro por nombre (compatibilidad) |
| GET | `/usuarios` | Listar usuarios |
| GET | `/usuarios/me` | Datos del usuario actual (requiere token) |
| GET | `/usuarios/{id}/presencia` | Estado de conexión |
| POST | `/usuarios/presencia/bulk` | Estado de varios usuarios |
| POST | `/mensaje_privado` | Enviar mensaje privado persistente |
| POST | `/mensaje_privado/sin_memoria` | Mensaje solo en vivo, no se guarda |
| GET | `/conversacion/{id}/{contacto_id}` | Conversación entre dos usuarios |
| GET | `/no_leidos/{id}` | Mensajes no leídos por contacto |
| DELETE | `/no_leidos/{id}/{contacto}` | Marcar como leído |
| POST | `/grupos` | Crear grupo público |
| GET | `/grupos/buscar` | Buscar grupos por nombre |
| GET | `/grupos/mios` | Grupos del usuario |
| POST | `/grupos/{id}/unirse` | Unirse a un grupo |
| GET | `/grupos/{id}/mensajes` | Mensajes del grupo |
| POST | `/grupos/{id}/mensajes` | Enviar mensaje al grupo |
| POST | `/ia/mensaje` | Enviar mensaje a Lumi |
| POST | `/ia/mensaje/modo` | Enviar a Lumi eligiendo modo |
| GET | `/ia/estado` | Estado de Lumi |
| POST | `/interno/notificar` | Endpoint interno del worker |
| WS | `/ws/{usuario_id}` | WebSocket en tiempo real |

> El token JWT no va en la URL del WebSocket: el cliente lo envía como primer
> mensaje. Esto evita que quede en logs.

### Ejemplo: iniciar sesión por correo

```bash
# Primer intento con correo nuevo (sin nombre)
curl -X POST http://localhost/api/usuarios/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com"}'

# Si pide nombre, lo incluimos
curl -X POST http://localhost/api/usuarios/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "nombre": "Alice"}'
```

La respuesta trae `id`, `nombre` y `token`. El email **no aparece** en la
respuesta.

---

## 🔵 Comandos del Makefile

> Solo funcionan en WSL / Ubuntu. En PowerShell usa los comandos Docker
> completos que aparecen en cada caso.

### Producción

| Comando | Equivalente PowerShell | Qué hace |
|---|---|---|
| `make prod-up` | `docker compose -f docker-compose.prod.yml up -d` | Levantar |
| `make prod-down` | `docker compose -f docker-compose.prod.yml down` | Detener |
| `make prod-pull` | `docker compose -f docker-compose.prod.yml pull` | Actualizar imágenes |
| `make prod-logs` | `docker compose -f docker-compose.prod.yml logs -f` | Ver logs |
| `make prod-status` | `docker compose -f docker-compose.prod.yml ps` | Ver estado |

### Mantenimiento (solo con el repositorio completo)

| Comando | Qué hace |
|---|---|
| `make clean` | Borra **todo**: chats, usuarios, grupos, modelo IA (pide confirmación) |
| `make disk` | Muestra uso de disco de Docker |
| `make prune` | Limpia caché sin tocar datos |

---

## 🔵 Estructura del proyecto

```
proyecto-chat-distribuido/
├── app/                        # Backend Python (FastAPI)
│   ├── main.py                 # Arranque, middleware y ciclo de vida
│   ├── auth.py                 # Autenticación JWT
│   ├── models.py               # Modelos Pydantic
│   ├── database.py             # Conexión MariaDB y creación de tablas
│   ├── cache.py                # Redis: caché, locks, presencia
│   ├── queue.py                # RabbitMQ
│   ├── worker.py               # Consumidor de mensajes
│   ├── request_id.py           # Trazabilidad
│   ├── logging_config.py       # Configuración de logs
│   └── routers/
│       ├── usuarios.py         # Login, registro, presencia
│       ├── mensajes.py         # Mensajes privados y sin memoria
│       ├── grupos.py           # Grupos públicos
│       ├── ia.py               # Lumi
│       ├── websocket.py        # Conexiones en tiempo real
│       └── interno.py          # Endpoint del worker
├── frontend/                   # React + Vite + Tailwind
│   ├── src/components/         # Componentes de UI
│   ├── src/services/           # Cliente HTTP y WebSocket
│   ├── src/hooks/              # Hooks (presencia)
│   ├── src/utils/              # Avatar, tiempo
│   ├── Dockerfile              # Build Node → Nginx
│   └── nginx.conf              # Proxy /api y /ws
├── tests/                      # Pruebas pytest
├── .github/workflows/docker.yml
├── docker-compose.yml          # Desarrollo (build local)
├── docker-compose.prod.yml     # Producción (DockerHub)
├── Dockerfile / Dockerfile.worker
├── Makefile
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔵 Instalación para desarrollo

Solo si quieres **modificar el código fuente**. Si no, usa la
[guía normal](#guía-de-instalación-5-pasos).

```bash
git clone https://github.com/crisdata/proyecto-chat-distribuido.git
cd proyecto-chat-distribuido
cp .env.example .env

# Reemplazar claves de ejemplo
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')|" .env
sed -i "s|^WORKER_SECRET=.*|WORKER_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')|" .env

# Construir y levantar (primer build: 5-10 min)
make up
make pull-model
```

La app queda en http://localhost. Para aplicar cambios:

```bash
# Backend
docker compose up --build -d api worker

# Frontend
docker compose build --no-cache frontend
docker compose up -d --force-recreate frontend
```

---

## 🔵 Camino alternativo con WSL / Ubuntu

Si prefieres usar WSL (Ubuntu dentro de Windows) en lugar de PowerShell, esta
es la guía equivalente.

### Requisitos extra

Instala Python, Make y Git dentro de Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-pip make git
```

Activa la integración con Docker Desktop: **Settings → Resources → WSL
Integration → Enable integration with my default WSL distro → Apply &
restart**.

### Paso a paso

```bash
# 1. Descargar archivos
mkdir vibe-deploy && cd vibe-deploy
curl -L -o docker-compose.prod.yml https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/docker-compose.prod.yml
curl -L -o .env https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/.env.example
curl -L -o Makefile https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/Makefile

# 2. Generar claves
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')|" .env
sed -i "s|^WORKER_SECRET=.*|WORKER_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')|" .env
grep -E 'JWT_SECRET|WORKER_SECRET' .env

# 3. Levantar
make prod-up

# 4. Verificar
make prod-status

# 5. Abre http://localhost en tu navegador

# 6. Descargar modelo de IA (opcional)
make prod-pull-model
```

---

## Licencia

Proyecto académico — Ingeniería de Sistemas, COTECNOVA.
Código disponible públicamente con fines educativos.
