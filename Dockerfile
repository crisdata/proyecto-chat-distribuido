# Imagen base oficial de Python 3.12 en su versión ligera
FROM python:3.12-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar primero solo las dependencias para aprovechar el caché de Docker.
# Si el código cambia pero requirements.txt no, Docker no reinstala todo.
COPY requirements.txt .

# Instalar dependencias sin guardar caché para mantener la imagen liviana
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código fuente
COPY . .

# Puerto que expone la API
EXPOSE 8000

# Comando para arrancar el servidor
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
