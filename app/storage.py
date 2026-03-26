# storage.py
# Almacenamiento en memoria del sistema.
# Aquí viven los datos mientras el servidor está en ejecución.
# En el Corte 2 este archivo será reemplazado por la conexión a MariaDB.

# Diccionario de usuarios registrados.
# Estructura: { "uuid": { "id": "uuid", "nombre": "alice" } }
usuarios = {}

# Diccionario de conversaciones.
# Estructura: { "uuid_receptor": [ { mensaje1 }, { mensaje2 } ] }
conversaciones = {}
