# Vibe — Red social universitaria con privacidad real

> Sistema distribuido de mensajería que combina chat privado entre usuarios
> humanos con una compañera virtual empática llamada **Lumi**, todo ejecutado
> localmente sin enviar datos a servicios externos.

**Autores:** Cristian Giraldo & Sebastián Pérez  
**Curso:** Programación Distribuida — COTECNOVA  
**Repositorio:** https://github.com/crisdata/proyecto-chat-distribuido

[![Build Status](https://github.com/crisdata/proyecto-chat-distribuido/actions/workflows/docker.yml/badge.svg)](https://github.com/crisdata/proyecto-chat-distribuido/actions)

---

## Tabla de contenido

1. [¿Qué es Vibe?](#-qué-es-vibe)
2. [Características principales](#-características-principales)
3. [Requisitos previos](#-requisitos-previos)
4. [Instalación rápida (recomendada)](#-instalación-rápida-recomendada)
5. [Cómo probar el sistema](#-cómo-probar-el-sistema)
6. [Acceso a las interfaces](#-acceso-a-las-interfaces)
7. [Herramientas de observabilidad](#-herramientas-de-observabilidad)
8. [Endpoints de la API](#-endpoints-de-la-api)
9. [Comandos del Makefile](#-comandos-del-makefile)
10. [Arquitectura del sistema](#-arquitectura-del-sistema)
11. [Despliegue automatizado (CI/CD)](#-despliegue-automatizado-cicd)
12. [Solución de problemas](#-solución-de-problemas-comunes)
13. [Estructura del proyecto](#-estructura-del-proyecto)
14. [Instalación para desarrollo](#-instalación-para-desarrollo)

---

## 💡 ¿Qué es Vibe?

**Vibe** es una red social universitaria diseñada con un enfoque diferente al
de las aplicaciones de mensajería tradicionales: **privacidad real** y
**conexiones humanas genuinas**. Permite que varios usuarios se registren y
conversen entre sí mediante mensajes privados en tiempo real, e incluye una
inteligencia artificial llamada **Lumi** que actúa como compañera virtual
empática del sistema.

### ¿Qué hace especial a Vibe?

- 🤖 **Lumi**, una IA empática integrada al chat que conversa con los usuarios.
  A diferencia de asistentes como ChatGPT, **Lumi se ejecuta 100% localmente**:
  ningún mensaje del usuario sale del sistema.
- 🔒 **Arquitectura privacy-first**: tres redes Docker aisladas siguiendo OWASP.
- ⚡ **Mensajería en tiempo real** mediante WebSocket.
- 🛡️ **Resiliencia probada**: el sistema se recupera automáticamente de fallos
  en sus componentes (base de datos, broker, IA).
- 👀 **Observabilidad completa**: cuatro paneles web para monitorear el sistema.

---

## ⭐ Características principales

| Característica | Descripción |
|---|---|
| 💬 **Chat privado entre usuarios** | Mensajes persistidos en MariaDB con autenticación JWT |
| 🔥 **Mensajes autodestructivos** | Modo efímero: los mensajes se eliminan solos a los 30 segundos |
| 🤖 **Lumi: compañera virtual con IA local** | Conversaciones empáticas sin enviar datos a terceros |
| 🟢 **Sistema de presencia en tiempo real** | Indicadores de conexión con TTL en Redis |
| 🔔 **Notificaciones por contacto** | Contadores individualizados estilo WhatsApp |
| ⚡ **WebSocket con reconexión automática** | Backoff exponencial de 1s a 30s |
| 📨 **Mensajería desacoplada** | RabbitMQ + worker con reintentos exponenciales |
| 🔐 **Autenticación JWT con revocación** | Tokens almacenados en Redis para invalidación inmediata |
| 🔒 **Locks distribuidos atómicos** | Scripts Lua en Redis para evitar race conditions |
| 🌐 **Tres redes Docker segmentadas** | Capas pública, aplicación y datos siguiendo OWASP |
| 🔍 **Trazabilidad completa** | `request_id` único viaja por todo el sistema |
| 📊 **Observabilidad** | Dozzle + Portainer + RabbitMQ Management + Redis Commander |
| 🚀 **CI/CD automatizado** | GitHub Actions + DockerHub (build automático en 45s) |
| ⚙️ **Operación simplificada** | Makefile con comandos cortos para todas las operaciones |

---

## 📋 Requisitos previos

Para instalar y ejecutar Vibe necesitas tener instalado en tu computadora lo
siguiente.

### Software obligatorio

| Software | Versión mínima | ¿Dónde se usa? | Cómo verificar |
|---|---|---|---|
| **Docker Engine** | 24.0 o superior | Ejecuta los contenedores | `docker --version` |
| **Docker Compose** | v2.20 o superior | Orquesta los servicios | `docker compose version` |
| **Python** | 3.10 o superior | Generar secretos de seguridad | `python3 --version` |
| **Make** | 4.0 o superior | Atajos para operar el sistema | `make --version` |
| **Git** | 2.30 o superior | Descargar archivos del repositorio | `git --version` |

> 💡 **Las instrucciones específicas para instalar cada uno de estos software
> en tu sistema operativo (Windows, Mac o Linux) están detalladas paso a paso
> en la sección [Notas por sistema operativo](#notas-por-sistema-operativo)
> más abajo.**

### Recursos de hardware

| Componente | Sin Ollama (modo fallback) | Con Ollama (IA real) |
|---|---|---|
| **Procesador** | 2 núcleos | 4 núcleos (Intel i5 / AMD Ryzen 5 o superior) |
| **Memoria RAM** | 4 GB | 8 GB (recomendado 16 GB) |
| **Almacenamiento** | 2 GB libres | 10 GB libres |
| **Internet** | Solo durante instalación | Solo durante instalación |

> 💡 **¿Poca RAM?** Si tu equipo tiene 4-6 GB de RAM, podés usar Vibe sin
> descargar el modelo de IA. Lumi responderá con mensajes empáticos
> predefinidos (modo "reposando"). La experiencia de chat entre usuarios
> funciona igual. Los límites de memoria en Docker están configurados para
> que el sistema no se descontrole en equipos con pocos recursos.

### Notas por sistema operativo

A continuación se detalla cómo instalar cada uno de los software obligatorios
según tu sistema operativo.

#### Windows (con WSL — recomendado)

**Paso 1 — Instalar Docker Desktop (incluye Docker Engine + Docker Compose)**

1. Descarga el instalador desde https://www.docker.com/products/docker-desktop
2. Ejecuta el instalador y seguí los pasos predeterminados
3. Reiniciá el computador cuando termine
4. Abrí Docker Desktop desde el menú de inicio
5. Esperá a que el ícono en la barra de tareas se ponga verde (estable)

**Paso 2 — Instalar WSL2**

Docker Desktop en Windows requiere WSL2. Normalmente Docker Desktop lo
configura automáticamente, pero si no:

1. Abrí **PowerShell como administrador** (click derecho → "Ejecutar como administrador")
2. Ejecutá:
   ```powershell
   wsl --install
   ```
3. Reiniciá el computador cuando termine

**Paso 3 — Abrir la terminal Ubuntu**

Buscá **Ubuntu** en el menú de inicio y abrilo. Esta terminal es donde
vas a ejecutar **todos los comandos** de este README.

> ⚠️ **NUNCA uses PowerShell ni CMD para los comandos de instalación.**
> Siempre en la terminal de Ubuntu/WSL.

**Paso 4 — Instalar Python, Make y Git en WSL**

Dentro de la terminal Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-pip make git
```

**Paso 5 — Verificar las instalaciones**

```bash
docker --version
docker compose version
python3 --version
make --version
git --version
```

> 💡 **¿No tenés WSL o preferís usar PowerShell directamente?** Saltá a la
> sección [Windows sin WSL (PowerShell)](#windows-sin-wsl-powershell).

#### Mac

**Paso 1 — Instalar Docker Desktop**

1. Descarga el instalador desde https://www.docker.com/products/docker-desktop
2. Arrastra Docker.app a la carpeta Aplicaciones
3. Abre Docker Desktop desde Launchpad
4. Acepta los permisos que solicite
5. Espera a que el ícono en la barra superior se ponga estable

**Paso 2 — Instalar las herramientas de desarrollo de Xcode**

Esto incluye Git y Make automáticamente:

```bash
xcode-select --install
```

Aparecerá una ventana solicitando aceptar la instalación. Acepta y espera
(puede tomar 10-15 minutos).

**Paso 3 — Instalar Python 3**

Si no tienes Python 3 instalado:

**Opción A — Con Homebrew (recomendado):**

```bash
# Si no tienes Homebrew, instalarlo primero:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Luego instalar Python:
brew install python@3.11
```

**Opción B — Descargar instalador oficial:**

Descarga desde https://www.python.org/downloads/macos/

**Paso 4 — Verificar todas las instalaciones**

```bash
docker --version
docker compose version
python3 --version
make --version
git --version
```

#### Windows sin WSL (PowerShell)

Si no querés o no podés usar WSL, podés ejecutar Vibe directamente desde
PowerShell. **No necesitás instalar Make ni Python** en este caso, porque
usarás los comandos directos de Docker en lugar del Makefile.

> ⚠️ **Limitación:** los comandos `make` no funcionan en PowerShell. En cada
> paso de la instalación rápida se muestra el comando alternativo para
> PowerShell.

**Paso 1 — Instalar Docker Desktop**

1. Descargalo desde https://www.docker.com/products/docker-desktop
2. Instalalo con las opciones predeterminadas
3. Reiniciá y abrí Docker Desktop
4. Esperá a que el ícono esté verde

**Paso 2 — Instalar Git**

Descargá el instalador desde https://git-scm.com/download/win e instálalo
con las opciones predeterminadas. Esto te da `git` y una terminal Git Bash
que también podés usar si preferís.

**Paso 3 — Verificar**

Abrí PowerShell y ejecutá:

```powershell
docker --version
docker compose version
git --version
```

Con eso ya podés seguir la instalación rápida usando los comandos
alternativos para PowerShell que aparecen en cada paso.

#### Linux (Ubuntu/Debian)

**Paso 1 — Instalar Docker Engine y Docker Compose**

Sigue la guía oficial: https://docs.docker.com/engine/install/ubuntu/

Comandos resumidos:

```bash
# Eliminar versiones antiguas
sudo apt remove docker docker-engine docker.io containerd runc

# Instalar Docker
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

**Paso 2 — Permitir usar Docker sin sudo**

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Cierra sesión y vuelve a iniciar para que los cambios surtan efecto.

**Paso 3 — Instalar Python, Make y Git**

Make y Git suelen venir preinstalados en la mayoría de distribuciones. Si no:

```bash
sudo apt install -y python3 python3-pip make git
```

**Paso 4 — Verificar todas las instalaciones**

```bash
docker --version
docker compose version
python3 --version
make --version
git --version
```

### Verificación previa al despliegue

Antes de instalar Vibe, ejecuta estos comandos para confirmar que tienes todo
lo necesario. Cada uno debe mostrar un número de versión:

```bash
docker --version
# Esperado: Docker version 24.x.x o superior

docker compose version
# Esperado: Docker Compose version v2.20.x o superior

python3 --version
# Esperado: Python 3.10.x o superior

make --version
# Esperado: GNU Make 4.x

git --version
# Esperado: git version 2.30.x o superior
```

Si **algún comando falla** con "command not found", revisa los pasos
correspondientes a tu sistema operativo antes de continuar.

---

## 🚀 Instalación rápida (recomendada)

> 🎯 **Tiempo total estimado:** 3-5 minutos
> (sin contar la descarga opcional del modelo de IA)

> ### ⚠️ ¡Importante! Si estás en Windows
>
> **Todos los comandos de esta guía deben ejecutarse en una terminal
> Ubuntu/WSL, NO en PowerShell ni CMD.**
>
> Si ya instalaste Docker Desktop, WSL viene incluido. Buscá **"Ubuntu"**
> en el menú de inicio. Si no lo encontrás, volvé a la sección
> [Notas por sistema operativo → Windows](#windows) para instalarlo.
>
> **¿No querés usar WSL?** Podés usar PowerShell, pero los comandos `make`
> no funcionan. En ese caso, reemplazá cada `make <comando>` por su
> equivalente directo que se muestra entre paréntesis en cada paso.

Esta es la forma **más rápida y práctica** de desplegar Vibe en cualquier
equipo. Utiliza las imágenes pre-construidas que el pipeline de CI/CD publica
automáticamente en DockerHub, por lo que **no necesitas clonar el repositorio
completo ni construir el código fuente localmente**.

> 💡 **¿Cuándo NO usar este método?** Solo si planeas **modificar el código
> fuente** del proyecto. En ese caso ve a
> [Instalación para desarrollo](#-instalación-para-desarrollo) al final del
> documento.

### Paso 1 — Descargar los archivos

Abrí tu terminal y ejecutá:

**WSL / Mac / Linux:**
```bash
mkdir vibe-deploy && cd vibe-deploy
curl -O https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/docker-compose.prod.yml
curl -O https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/.env.example
curl -O https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/Makefile
mv .env.example .env
```

**PowerShell (Windows sin WSL):**
```powershell
mkdir vibe-deploy; cd vibe-deploy
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/docker-compose.prod.yml" -OutFile "docker-compose.prod.yml"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/.env.example" -OutFile ".env.example"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/crisdata/proyecto-chat-distribuido/main/Makefile" -OutFile "Makefile"
Rename-Item .env.example .env
```

### Paso 2 — Generar los secretos

**WSL / Mac / Linux:**
```bash
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(48))" >> .env
python3 -c "import secrets; print('WORKER_SECRET=' + secrets.token_urlsafe(48))" >> .env
```

**PowerShell:** (no necesita Python — usa .NET)
```powershell
Add-Content .env "JWT_SECRET=$([Convert]::ToBase64String((1..48 | %{ Get-Random -Max 256 })))"
Add-Content .env "WORKER_SECRET=$([Convert]::ToBase64String((1..48 | %{ Get-Random -Max 256 })))"
```

### Paso 3 — Levantar el sistema

**WSL / Mac / Linux:**
```bash
make prod-up
```

**PowerShell:**
```powershell
docker compose -f docker-compose.prod.yml up -d
```

> ⏱️ La primera vez tarda 3-5 minutos (descarga ~600 MB).

### Paso 4 — Abrir la aplicación

Esperá 30 segundos y abrí tu navegador en:

### 👉 **http://localhost**

🎉 **¡Listo!** Registrate con cualquier nombre y empezá a chatear.

> 💡 **¿Querés activar la IA?** Ejecutá `make prod-pull-model` (o en
> PowerShell:
> [ver instrucciones](#paso-7-opcional--descargar-el-modelo-de-ia-para-activar-a-lumi)).
> Sin este paso, Lumi responde con mensajes predefinidos.

---

### Paso 7 (opcional) — Descargar el modelo de IA para activar a Lumi

Sin este paso, **Lumi responde con mensajes empáticos pre-diseñados** (modo
"reposando" con fallback). Si quieres que Lumi responda con IA real generada
por el modelo, debes descargarlo.

> ⚠️ **¿Por qué es un paso aparte?** El contenedor de Ollama está en una red
> aislada sin acceso a internet (por seguridad). Para descargar el modelo,
> debemos conectarlo temporalmente a internet, descargar, y volver a aislarlo.
> Este procedimiento está automatizado por el Makefile.

**WSL / Mac / Linux:**
```bash
make prod-pull-model
```

**PowerShell:**
```powershell
$NETWORK = docker network ls --format "{{.Name}}" | Select-String "public_network"
docker network connect $NETWORK chat_ollama
docker exec -i chat_ollama ollama pull llama3.2:3b
docker network disconnect $NETWORK chat_ollama
```

> ⏱️ **Tiempo estimado:** 3-10 minutos (el modelo pesa ~2 GB).

El comando hace automáticamente:
1. Detecta el nombre exacto de la red pública de Docker
2. Conecta Ollama a internet temporalmente
3. Descarga el modelo llama3.2:3b
4. Desconecta Ollama de internet (vuelve al aislamiento)

Al terminar, verifica que el modelo quedó instalado:

```bash
docker exec chat_ollama ollama list
```

Debes ver:

```
NAME            ID              SIZE      MODIFIED
llama3.2:3b     a80c4f17acd5    2.0 GB    1 minute ago
```

> 💡 **El modelo se queda almacenado en un volumen Docker** y sobrevive a
> reinicios. Solo necesitas hacer esto una vez.

---

## 🧪 Cómo probar el sistema

Para validar que todo funciona correctamente, prueba estos tres escenarios:

### Prueba 1: Chat entre dos usuarios

1. En la pantalla de registro, ingresa con el nombre **Alice**
2. Abre una **segunda pestaña en modo incógnito** (Ctrl+Shift+N en Chrome)
3. En esa pestaña ve a http://localhost e ingresa como **Bob**
4. En la pestaña de Alice, verás a **Bob** aparecer automáticamente en la lista
5. Click en Bob y escríbele un mensaje
6. Cambia a la pestaña de Bob: deberías ver el mensaje al instante

✅ **Si funciona:** WebSocket, base de datos y notificaciones operan correctamente.

### Prueba 2: Conversación con Lumi

1. En la lista de contactos, verás a **Lumi** anclada arriba (con avatar púrpura)
2. Click en Lumi
3. Escríbele: "Hola Lumi, ¿cómo estás?"
4. Espera unos segundos (la primera respuesta puede tardar 30-60s en CPU)
5. Lumi responderá con un mensaje empático

✅ **Si responde con un mensaje natural:** la IA está funcionando correctamente.
✅ **Si responde "Estoy descansando un rato..." u otro fallback:** el modelo
   no está cargado, ejecuta `make prod-pull-model`.

### Prueba 3: Trazabilidad con request_id

1. Abre Dozzle en http://localhost:9999
2. Click en `chat_api` en la lista de la izquierda
3. En la app, envía un mensaje
4. En Dozzle busca una línea como:
   ```
   2026-XX-XX ... INFO - [queue] [b7d4a2e1] Evento publicado en cola 'mensajes'
   ```
5. Copia el ID entre corchetes (en este ejemplo, `b7d4a2e1`)
6. Pégalo en el buscador de Dozzle (parte superior)
7. Cambia entre `chat_api` y `chat_worker`: verás varias líneas con el mismo ID,
   demostrando cómo el mensaje viaja por todo el sistema

✅ **Si las líneas aparecen:** la trazabilidad distribuida funciona correctamente.

---

## 🌐 Acceso a las interfaces

Una vez el sistema está corriendo, tienes acceso a varias interfaces web:

| Interfaz | URL | Credenciales | Propósito |
|---|---|---|---|
| 💬 **App Vibe** | http://localhost | (registro libre) | Aplicación principal |
| 📚 **Swagger (API docs)** | http://localhost/api/docs | (sin credenciales) | Documentación interactiva de la API |
| 📋 **ReDoc (API docs alternativa)** | http://localhost/api/redoc | (sin credenciales) | Documentación legible de la API |
| 🐰 **RabbitMQ Management** | http://localhost:15672 | `guest` / `guest` | Panel del broker de mensajes |
| 🔍 **Redis Commander** | http://localhost:8081 | (sin credenciales) | Explorador de Redis |
| 📊 **Dozzle (logs)** | http://localhost:9999 | (sin credenciales) | Logs en vivo de todos los contenedores |
| 🐳 **Portainer** | http://localhost:9000 | (crear al primer ingreso) | Administrador de Docker |

### 📚 Swagger — Documentación interactiva de la API

Swagger UI permite **probar todos los endpoints de la API directamente desde
el navegador**, sin necesidad de herramientas externas como Postman.

**¿Cómo usarlo?**

1. Abre **http://localhost/api/docs**
2. Verás todos los endpoints organizados por sección (usuarios, mensajes, IA, etc.)
3. Click en cualquier endpoint para expandirlo
4. Click en **"Try it out"**
5. Completa los parámetros requeridos
6. Click en **"Execute"**
7. Verás la respuesta en tiempo real con el código HTTP y el cuerpo JSON

**Endpoint útil para empezar:** `POST /usuarios` para registrar un usuario nuevo.

---

## 🔍 Herramientas de observabilidad

El sistema incluye cuatro paneles web para monitorear lo que ocurre en tiempo real.

### Dozzle — Logs unificados

**URL:** http://localhost:9999

Muestra los logs de todos los contenedores en una interfaz limpia.

**Funciones útiles:**
- Lista de contenedores a la izquierda
- Click en cualquier contenedor muestra sus logs en vivo
- Filtro de texto en la parte superior
- Botón para ver varios contenedores a la vez

### Redis Commander — Explorador de Redis

**URL:** http://localhost:8081

Permite inspeccionar las claves almacenadas en Redis.

**Claves típicas:**

| Patrón | Significado |
|---|---|
| `usuario:<uuid>` | Caché del usuario |
| `sesion:<uuid>` | Token JWT activo |
| `presencia:<uuid>` | Usuario actualmente conectado |
| `no_leidos:<receptor>:<emisor>` | Mensajes no leídos de un contacto específico |
| `lock:registro:<nombre>` | Lock distribuido durante registro |
| `ia:id` | UUID del nodo Lumi |

### RabbitMQ Management — Panel del broker

**URL:** http://localhost:15672 — **Credenciales:** `guest` / `guest`

Muestra colas, conexiones, consumidores y tráfico.

**Para ver mensajes pasando:** pestaña **Queues** → click en `mensajes`.

### Portainer — Administrador web de Docker

**URL:** http://localhost:9000

Interfaz visual para administrar todos los contenedores, imágenes, redes y
volúmenes del sistema. Al primer ingreso pide crear un usuario administrador
con contraseña de mínimo 12 caracteres.

---

## 🔌 Endpoints de la API

La API expone los siguientes endpoints. **La forma recomendada de explorarlos
es mediante Swagger UI en http://localhost/api/docs.**

### Tabla completa

| Método | Endpoint | Autenticación | Descripción |
|---|---|---|---|
| GET | `/` | No | Estado del sistema |
| POST | `/usuarios` | No | Registrar o reingresar usuario |
| GET | `/usuarios` | No | Listar todos los usuarios |
| GET | `/usuarios/me` | JWT | Datos del usuario autenticado |
| GET | `/usuarios/{id}/presencia` | No | Estado de conexión de un usuario |
| POST | `/usuarios/presencia/bulk` | No | Estado de conexión de varios usuarios |
| POST | `/mensaje_privado` | JWT | Enviar mensaje privado (con soporte para autodestrucción vía `expira_en`) |
| GET | `/conversacion/{id}` | JWT | Historial de mensajes recibidos (legado, paginado) |
| GET | `/conversacion/{id}/{contacto_id}` | JWT | Conversación bilateral completa (paginada por cursor) |
| GET | `/no_leidos/{id}` | JWT | Mensajes no leídos por contacto |
| DELETE | `/no_leidos/{id}/{contacto}` | JWT | Marcar conversación como leída |
| POST | `/ia/mensaje` | JWT | Enviar mensaje a Lumi |
| GET | `/ia/estado` | No | Verificar disponibilidad de Lumi |
| POST | `/interno/notificar` | Worker secret | Endpoint interno (usado por el worker) |
| WS | `/ws/{usuario_id}` | JWT (1er mensaje) | Conexión WebSocket en tiempo real |

### Ejemplos prácticos con cURL

**Registrar un usuario:**

```bash
curl -X POST http://localhost/api/usuarios \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Alice"}'
```

Respuesta:

```json
{
  "id": "37b5b1c3-92d8-439b-8d2f-df0773eb4d5e",
  "nombre": "Alice",
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Listar todos los usuarios:**

```bash
curl http://localhost/api/usuarios
```

**Enviar mensaje a Lumi** (necesita el token JWT del registro anterior):

```bash
curl -X POST http://localhost/api/ia/mensaje \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -d '{"contenido": "Hola Lumi"}'
```

**Consultar estado de Lumi:**

```bash
curl http://localhost/api/ia/estado
```

Respuesta cuando Lumi está disponible:

```json
{
  "disponible": true,
  "modelo": "llama3.2:3b"
}
```

---

## 🎮 Comandos del Makefile

El proyecto incluye un **Makefile** con atajos para todas las operaciones del
sistema. Es la forma recomendada de operar el proyecto porque evita escribir
comandos largos y reduce errores.

Para ver todos los comandos disponibles con su descripción:

```bash
make help
```

### Comandos para modo producción (imágenes de DockerHub)

Estos son los comandos para operar el sistema cuando usas las imágenes ya
construidas. **Son los que utilizaste en la instalación rápida**.

| Comando | Qué hace |
|---|---|
| `make prod-up` | Levanta el sistema descargando imágenes desde DockerHub |
| `make prod-down` | Detiene los contenedores conservando datos |
| `make prod-pull` | Actualiza las imágenes a la última versión publicada |
| `make prod-pull-model` | Descarga el modelo de IA para activar Lumi |
| `make prod-logs` | Muestra logs del sistema en vivo |
| `make prod-status` | Muestra el estado de los contenedores |

### Comandos para modo desarrollo (build desde código fuente)

Solo aplican si clonaste el repositorio completo
(ver [Instalación para desarrollo](#-instalación-para-desarrollo)):

| Comando | Qué hace |
|---|---|
| `make up` | Construye desde código fuente y levanta todo |
| `make down` | Detiene todos los servicios (conserva datos) |
| `make restart` | Reinicia todo (down + up) |
| `make ps` | Muestra el estado de los contenedores |
| `make logs` | Muestra logs de todos los servicios en vivo |
| `make build` | Reconstruye las imágenes sin levantar |
| `make pull-model` | Descarga el modelo de IA para Lumi |

### Comandos de mantenimiento

| Comando | Qué hace | Cuándo usar |
|---|---|---|
| `make reset-db` | Limpia mensajes y usuarios | Antes de presentar una demo |
| `make clean` | ⚠️ Borra TODOS los datos persistentes | Solo para resetear de cero |
| `make disk` | Muestra uso de disco de Docker | Para diagnóstico |
| `make prune` | Limpia caché de builds antiguos | Mantenimiento semanal |
| `make prune-all` | Limpieza profunda con confirmación | Antes de entregas o instalaciones limpias |

---

## 🏗️ Arquitectura del sistema

El sistema está compuesto por **10 contenedores Docker** organizados en
**3 redes aisladas**:

```
┌──────────────────────────────────────────────────────────────┐
│                      public_network                           │
│   (Única capa accesible desde el navegador del usuario)       │
│                                                                │
│  ┌──────────┐   ┌──────────┐   ┌─────────┐   ┌────────────┐ │
│  │  Nginx   │──▶│ FastAPI  │   │ Dozzle  │   │   Redis    │ │
│  │   :80    │WS │  :8000   │   │  :9999  │   │ Commander  │ │
│  │(Frontend)│   │(chat_api)│   │ (logs)  │   │   :8081    │ │
│  └──────────┘   └────┬─────┘   └─────────┘   └────┬───────┘ │
│                      │                              │         │
│  ┌────────────┐      │                              │         │
│  │ Portainer  │      │                              │         │
│  │   :9000    │      │                              │         │
│  └────────────┘      │                              │         │
└──────────────────────┼──────────────────────────────┼────────┘
                       │                              │
        ┌──────────────┼─────────────┐                │
        │              │             │                │
┌───────▼──────┐       │   ┌─────────▼────────────────▼─────┐
│ app_network  │       │   │      data_network              │
│ (internal)   │       │   │      (internal)                │
│              │       │   │                                 │
│ ┌──────────┐ │       │   │ ┌─────────┐  ┌──────┐         │
│ │ RabbitMQ │ │       │   │ │MariaDB11│  │Redis │         │
│ │  :5672   │ │       │   │ └─────────┘  └──────┘         │
│ └─────┬────┘ │       │   │ ┌──────────────────────────┐   │
│       │      │       │   │ │ Ollama llama3.2:3b (Lumi)│   │
│ ┌─────▼────┐ │       │   │ └──────────────────────────┘   │
│ │  Worker  │ │       │   └─────────────────────────────────┘
│ └──────────┘ │       │
└──────────────┘       │
```

### Componentes y sus responsabilidades

| Componente | Tecnología | Red | Rol |
|---|---|---|---|
| **Frontend** | React 19 + Vite + Tailwind + Nginx | public | Interfaz de usuario |
| **API** | FastAPI 0.135 + Uvicorn | public + app + data | Servidor principal |
| **Base de datos** | MariaDB 11 | data | Persistencia de mensajes y usuarios |
| **Caché y locks** | Redis 7 | data | Sesiones, presencia, coordinación |
| **IA (Lumi)** | Ollama llama3.2:3b | data | Compañera virtual empática |
| **Broker** | RabbitMQ 3.13 | app | Eventos asíncronos |
| **Worker** | Python asyncio + aio-pika | app + data | Procesa notificaciones |
| **Dozzle** | amir20/dozzle | (socket Docker) | Logs en tiempo real |
| **Redis Commander** | rediscommander | public + data | Explorador de Redis |
| **Portainer** | portainer/portainer-ce | (socket Docker) | Administrador Docker |

### Segmentación de redes (seguridad por diseño)

Las tres redes Docker tienen niveles progresivos de aislamiento siguiendo
las recomendaciones de **OWASP**:

- **public_network** → Capa de entrada. Único punto accesible desde fuera.
- **app_network** → Capa de mensajería. Marcada como `internal: true` (sin internet).
- **data_network** → Capa de datos. Marcada como `internal: true` (totalmente aislada).

**¿Por qué importa?** Si alguien comprometiera el frontend, no podría acceder
directamente a la base de datos: tendría que pasar primero por la API.

### Flujo completo de un mensaje en tiempo real

Cuando un usuario A envía un mensaje al usuario B:

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

Cada paso del 1 al 12 produce un log con el **mismo `request_id`**, lo que
permite trazar el flujo completo en Dozzle.

---

## 🚀 Despliegue automatizado (CI/CD)

El sistema cuenta con un **pipeline de CI/CD en GitHub Actions** que automatiza
la construcción y publicación de las imágenes Docker cada vez que se hace
push a la rama `main`.

### Imágenes publicadas en DockerHub

Las tres imágenes del sistema están disponibles públicamente en:
**https://hub.docker.com/u/crisdatap**

- `crisdatap/vibe-api:latest` — Backend FastAPI con WebSocket
- `crisdatap/vibe-worker:latest` — Worker consumidor de RabbitMQ
- `crisdatap/vibe-frontend:latest` — React + Nginx (build multi-stage)

Cada imagen tiene además una etiqueta específica con el SHA del commit
(por ejemplo, `crisdatap/vibe-api:80d811c`) para trazabilidad completa
y rollback rápido.

### Estructura del pipeline

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
        │   │ build-  │ │ build-  │ │build││  (en paralelo)
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

**Tiempo del pipeline:** ~45 segundos con caché habilitado.

### ¿Qué automatiza el pipeline?

Cada push a `main` desencadena automáticamente:

1. **Checkout** del código del repositorio
2. **Login** a DockerHub usando secrets seguros
3. **Build** de las tres imágenes en paralelo
4. **Tag dual** con `latest` y SHA del commit (para trazabilidad)
5. **Push** de las imágenes a DockerHub
6. **Notificación** del resultado

---

## 🛠️ Solución de problemas comunes

### "Cannot connect to the Docker daemon"

Docker Desktop no está corriendo.

**Solución:** Abre Docker Desktop desde el menú de inicio y espera a que el
ícono en la barra de tareas se ponga estable. Luego reintenta el comando.

### "Bind for 0.0.0.0:XXXX failed: port is already allocated"

Otro proceso usa ese puerto.

**Solución:**

```bash
# Comprueba si tienes contenedores viejos
docker ps -a
docker rm -f <nombre-del-contenedor-viejo>

# Si no es Docker, identifica el proceso (cambia el número de puerto)
sudo lsof -i :15672
```

### "El nodo IA no está disponible" / Lumi responde "Estoy descansando..."

El modelo de IA no está descargado. Esto es **comportamiento esperado** si
saltaste el Paso 7 de la instalación.

**Solución:**

```bash
make prod-pull-model
```

Si ya lo ejecutaste y no funciona, verifica:

```bash
docker exec chat_ollama ollama list
```

Si está vacío, vuelve a ejecutar `make prod-pull-model`.

### "ERROR: No se encontro ninguna red 'public_network'"

El sistema no está corriendo cuando intentas descargar el modelo.

**Solución:**

```bash
# Primero levanta el sistema
make prod-up

# Luego descarga el modelo
make prod-pull-model
```

### "Error al descargar el modelo: server misbehaving"

Problema de DNS durante la descarga.

**Solución:** El comando `make prod-pull-model` ya maneja la conexión y
desconexión de la red automáticamente. Si el error persiste, verifica que
tu conexión a internet funcione y reintenta.

### La API se reinicia en bucle

Faltan secretos en `.env`.

**Solución:**

```bash
# Verificar
grep -E "JWT_SECRET|WORKER_SECRET" .env

# Si no aparecen, regenerarlos
echo "JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" >> .env
echo "WORKER_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" >> .env

# Reiniciar la API
docker compose -f docker-compose.prod.yml restart api
```

### El frontend muestra HTML antiguo después de actualizar

Caché del navegador.

**Solución:**

```bash
# Actualizar a la versión más reciente desde DockerHub
make prod-pull
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

También: en DevTools (F12) → Network → marca "Disable cache" y recarga con
`Ctrl+Shift+R`.

### Disco lleno por imágenes Docker

```bash
make disk          # Ver cuánto ocupa
make prune         # Limpieza segura (no toca datos)
make prune-all     # Limpieza más profunda con confirmación
```

### Lumi tarda mucho en responder (más de 1 minuto)

Es normal en CPU. El modelo llama3.2:3b necesita procesamiento.

**Comportamiento esperado:**
- La **primera respuesta** después de arrancar puede tomar 30-60 segundos
  (carga del modelo en memoria)
- Las respuestas posteriores deberían ser de 3-15 segundos
- Si tu equipo tiene GPU, Ollama la usaría automáticamente

### Los contenedores muestran "unhealthy"

Algún servicio no pasó su healthcheck.

**Solución:**

```bash
# Ver logs específicos
docker logs chat_db --tail 30
docker logs chat_redis --tail 30
docker logs chat_rabbitmq --tail 30

# Reiniciar el servicio problemático
docker compose -f docker-compose.prod.yml restart <nombre_servicio>
```

### "make: command not found"

Make no está instalado.

**Solución:** Revisa la sección
[Notas por sistema operativo](#notas-por-sistema-operativo) para instalar
Make en tu sistema.

---

## 📁 Estructura del proyecto

```
proyecto-chat-distribuido/
├── app/                        # Backend Python
│   ├── main.py                 # Punto de entrada y middleware HTTP
│   ├── auth.py                 # Autenticación JWT y secreto del worker
│   ├── models.py               # Modelos de datos Pydantic
│   ├── database.py             # Pool de conexiones MariaDB
│   ├── cache.py                # Redis: caché, locks, contadores, sesiones
│   ├── queue.py                # Conexión RabbitMQ y publicación
│   ├── worker.py               # Worker que consume la cola
│   ├── request_id.py           # ContextVar para trazabilidad
│   ├── logging_config.py       # Configuración central de logging
│   └── routers/                # Endpoints de la API
│       ├── usuarios.py
│       ├── mensajes.py
│       ├── ia.py
│       ├── websocket.py
│       └── interno.py
├── frontend/                   # Frontend React
│   ├── src/
│   │   ├── components/         # Componentes UI
│   │   ├── services/           # Cliente HTTP y WebSocket
│   │   ├── hooks/              # Hooks personalizados (usePresencia)
│   │   ├── utils/              # Utilidades (avatarColors, tiempo)
│   │   ├── App.jsx             # Componente raíz
│   │   └── main.jsx            # Punto de entrada React
│   ├── Dockerfile              # Build multi-stage: Node → Nginx
│   └── nginx.conf              # Proxy /api, /ws y SPA fallback
├── .github/workflows/
│   └── docker.yml              # Pipeline CI/CD GitHub Actions
├── docs/                       # Documentación adicional
│   └── evidencias-fallos/      # Evidencias de pruebas de resiliencia
├── docker-compose.yml          # Orquestación desarrollo
├── docker-compose.prod.yml     # Orquestación producción (DockerHub)
├── Dockerfile                  # Imagen del backend Python
├── Dockerfile.worker           # Imagen del worker RabbitMQ
├── Makefile                    # Atajos para operación
├── requirements.txt            # Dependencias Python
├── .env.example                # Plantilla de variables
└── README.md                   # Este archivo
```

---

## 🛠️ Instalación para desarrollo

> ⚠️ **Esta sección solo aplica si quieres modificar el código fuente** del
> proyecto (frontend, backend, worker). Si solo quieres ejecutar Vibe, usa la
> [Instalación rápida](#-instalación-rápida-recomendada).

A diferencia de la instalación rápida que descarga imágenes ya construidas
desde DockerHub, esta instalación clona el repositorio completo y construye
las imágenes localmente desde el código fuente. Esto permite hacer cambios al
código y verlos reflejados al reconstruir.

### Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/crisdata/proyecto-chat-distribuido.git
cd proyecto-chat-distribuido
```

### Paso 2 — Crear el archivo de configuración

```bash
cp .env.example .env

# Generar los dos secretos requeridos
echo "JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" >> .env
echo "WORKER_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" >> .env

# Verificar
tail -3 .env
```

### Paso 3 — Construir y levantar el sistema

Construye las imágenes desde el código fuente y arranca los 10 contenedores:

```bash
make up
```

> ⏱️ **La primera vez tarda entre 5 y 10 minutos** porque Docker debe descargar
> imágenes base y construir el código del proyecto (compilar frontend, instalar
> dependencias Python, etc.). Las siguientes veces tarda solo unos segundos.

### Paso 4 — Verificar que todo arrancó correctamente

Espera 30 segundos y luego ejecuta:

```bash
make ps
```

Debes ver los 10 contenedores corriendo (igual que en la instalación rápida).

### Paso 5 — Descargar el modelo de IA para Lumi

```bash
make pull-model
```

### Paso 6 — Abrir la aplicación

Abre tu navegador en **http://localhost** y ya está.

### Flujo de trabajo de desarrollo

Después de modificar código:

```bash
# Si modificaste código backend (app/)
docker compose up --build -d api worker

# Si modificaste código frontend (frontend/)
docker compose build --no-cache frontend
docker compose up -d --force-recreate frontend

# Para ver logs en vivo
make logs

# Para reiniciar todo
make restart

# Para detener todo
make down
```

---

## 👥 Autores y créditos

Proyecto desarrollado para el curso de **Programación Distribuida** del programa
de **Ingeniería de Sistemas** en **COTECNOVA**.

**Autores:**
- **Cristian David Giraldo**
- **Juan Sebastián Pérez Guzmán**

**Profesor:** Jhon James Cano Sánchez

---

## 📄 Licencia

Este proyecto es de uso académico. El código está disponible públicamente
en el repositorio de GitHub para fines educativos y de aprendizaje.
