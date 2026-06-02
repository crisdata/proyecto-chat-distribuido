# Makefile — Atajos para operar el sistema de chat distribuido
# Uso: make <comando>
# Ejecuta "make help" para ver todos los comandos disponibles.

# Declara los nombres como objetivos "falsos" para que make no los
# confunda con archivos que tengan el mismo nombre.
.PHONY: help up down restart logs ps build clean reset-db pull-model status disk prune prune-all

# Comando por defecto cuando se ejecuta solo "make"
.DEFAULT_GOAL := help


# ── Comandos principales ──────────────────────────────────────────────

help:  ## Muestra esta ayuda con la lista de comandos disponibles
	@echo "Comandos disponibles:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

up:  ## Construye y levanta todos los servicios en segundo plano
	docker compose up --build -d
	@echo ""
	@echo "Sistema arrancado. Servicios disponibles:"
	@echo "  Aplicacion:       http://localhost"
	@echo "  Dozzle (logs):    http://localhost:9999"
	@echo "  RabbitMQ panel:   http://localhost:15672  (guest/guest)"
	@echo "  Redis Commander:  http://localhost:8081"
	@echo "  Portainer:        http://localhost:9000"

down:  ## Detiene todos los servicios conservando datos
	docker compose down

restart:  ## Reinicia todos los servicios (down + up)
	docker compose down
	docker compose up --build -d

logs:  ## Muestra los logs de todos los servicios en vivo (Ctrl+C para salir)
	docker compose logs -f

ps:  ## Muestra el estado de los contenedores
	docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

status: ps  ## Alias de "ps"


# ── Comandos avanzados ────────────────────────────────────────────────

build:  ## Reconstruye las imagenes sin levantar los contenedores
	docker compose build

clean:  ## Detiene los servicios y borra TODOS los datos (BD, modelo IA, etc)
	@echo "ATENCION: esto borra todos los datos persistentes."
	@read -p "Estas seguro? [s/N] " resp && [ "$$resp" = "s" ] || exit 1
	docker compose down -v
	@echo "Sistema reseteado completamente."

reset-db:  ## Borra solo mensajes y usuarios para una demo limpia
	docker exec -it chat_db mariadb -u chat_user -pchat1234 chat_db \
		-e "DELETE FROM mensajes; DELETE FROM usuarios;"
	docker compose restart api
	@echo "Base de datos limpiada y API reiniciada."

pull-model:  ## Descarga el modelo Ollama (conecta y desconecta de la red publica)
	@NETWORK_NAME=$$(docker network ls --format "{{.Name}}" | grep public_network | head -1); \
	if [ -z "$$NETWORK_NAME" ]; then \
		echo "ERROR: No se encontro ninguna red 'public_network'. Asegurate de que el sistema este corriendo (make up)."; \
		exit 1; \
	fi; \
	echo "Red detectada: $$NETWORK_NAME"; \
	echo "Conectando Ollama a la red publica temporalmente..."; \
	docker network connect $$NETWORK_NAME chat_ollama || true; \
	echo "Descargando modelo llama3.2:3b (puede tardar varios minutos)..."; \
	docker exec -it chat_ollama ollama pull llama3.2:3b; \
	echo "Desconectando Ollama de la red publica..."; \
	docker network disconnect $$NETWORK_NAME chat_ollama || true; \
	echo "Modelo descargado y Ollama aislado de nuevo."; \
	docker exec chat_ollama ollama list

	# ── Comandos de mantenimiento y limpieza ──────────────────────────────

disk:  ## Muestra el uso de disco de Docker (imagenes, volumenes, cache)
	@echo "Uso de disco Docker:"
	@docker system df
	@echo ""
	@echo "Para limpiar build cache y volumenes huerfanos: make prune"

prune:  ## Limpia build cache y volumenes huerfanos (seguro, no toca nada activo)
	@echo "Limpiando build cache..."
	docker builder prune -f
	@echo ""
	@echo "Limpiando volumenes huerfanos..."
	docker volume prune -f
	@echo ""
	@echo "Limpieza completada. Espacio liberado:"
	@docker system df

prune-all:  ## Limpieza profunda: cache, volumenes, contenedores parados e imagenes huerfanas
	@echo "ATENCION: esto borra cache, volumenes huerfanos, contenedores parados e imagenes sin uso."
	@read -p "Continuar? [s/N] " resp && [ "$$resp" = "s" ] || exit 1
	@echo "Limpiando build cache..."
	docker builder prune -f
	@echo ""
	@echo "Limpiando volumenes huerfanos..."
	docker volume prune -f
	@echo ""
	@echo "Limpiando contenedores parados..."
	docker container prune -f
	@echo ""
	@echo "Limpiando imagenes huerfanas..."
	docker image prune -f
	@echo ""
	@echo "Limpieza profunda completada:"
	@docker system df


# ── Comandos de PRODUCCIÓN (usar imágenes de DockerHub) ──────────────

prod-up: ## Levanta el sistema en modo producción (descarga imágenes de DockerHub)
	docker compose -f docker-compose.prod.yml up -d
	@echo ""
	@echo "Sistema Vibe arrancado en modo producción"
	@echo ""
	@echo "Accede a: http://localhost"
	@echo "API docs:  http://localhost/api/docs"
	@echo ""
	@echo "NOTA: Lumi (IA) está en modo 'reposando' hasta que descargues el modelo."
	@echo "      Para activarla, ejecuta: make prod-pull-model"

prod-down: ## Detiene el sistema en modo producción
	docker compose -f docker-compose.prod.yml down

prod-pull: ## Descarga las imágenes más recientes desde DockerHub
	docker compose -f docker-compose.prod.yml pull

prod-pull-model: ## Descarga el modelo de IA llama3.2:3b en producción
	prod-pull-model: ## Descarga el modelo de IA llama3.2:3b en producción
	@NETWORK_NAME=$$(docker network ls --format "{{.Name}}" | grep public_network | head -1); \
	if [ -z "$$NETWORK_NAME" ]; then \
		echo "ERROR: No se encontro ninguna red 'public_network'. Asegurate de que el sistema este corriendo (make prod-up)."; \
		exit 1; \
	fi; \
	echo "Red detectada: $$NETWORK_NAME"; \
	echo "Conectando Ollama a internet temporalmente..."; \
	docker network connect $$NETWORK_NAME chat_ollama || true; \
	echo "Descargando modelo llama3.2:3b (puede tardar varios minutos)..."; \
	docker exec -it chat_ollama ollama pull llama3.2:3b; \
	echo "Desconectando Ollama de internet..."; \
	docker network disconnect $$NETWORK_NAME chat_ollama || true; \
	echo ""; \
	echo "Modelo descargado. Lumi ya puede responder con la IA."

prod-logs: ## Muestra logs del sistema en producción
	docker compose -f docker-compose.prod.yml logs -f --tail=100

prod-status: ## Muestra el estado de los contenedores en producción
	docker compose -f docker-compose.prod.yml ps