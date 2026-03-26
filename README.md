# Chat Privado Usuario-Usuario
**Grupo 4 — Programación Distribuida**

---

## ¿Qué hace este sistema?

API REST que permite la comunicación privada entre usuarios registrados.
Cada usuario tiene un identificador único y puede enviar mensajes a otros
usuarios. El historial de conversaciones se mantiene en memoria mientras
el servidor está activo.

---

## Requisitos

- Python 3.10 o superior
- WSL (Ubuntu) o cualquier sistema Linux/Mac

---

## Instalación y ejecución

**1. Clonar el repositorio**
```bash
git clone https://github.com/crisdata/proyecto1.git
cd proyecto1
```

**2. Crear y activar el entorno virtual**
```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Instalar dependencias**
```bash
pip install -r requirements.txt
```

**4. Ejecutar el servidor**
```bash
uvicorn app.main:app --reload
```

**5. Abrir la documentación interactiva**  
Con el servidor corriendo, abrir en el navegador:  
http://127.0.0.1:8000/docs

---

## Endpoints disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | /usuarios | Registrar un nuevo usuario |
| POST | /mensaje_privado | Enviar un mensaje privado |
| GET | /conversacion/{usuario_id} | Consultar historial de mensajes |

---

## Estructura del proyecto
```
proyecto1/
├── app/
│   ├── main.py         # Punto de entrada
│   ├── models.py       # Estructura de datos
│   ├── storage.py      # Almacenamiento en memoria
│   └── routers/
│       ├── usuarios.py # Endpoint de usuarios
│       └── mensajes.py # Endpoints de mensajes
├── requirements.txt
└── README.md
```

---

## Corte 2 — Próximos pasos

- Persistencia con MariaDB
- Integración de nodo de inteligencia artificial local (Ollama)
