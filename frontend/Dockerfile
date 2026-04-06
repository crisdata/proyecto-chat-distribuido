# Etapa 1: construcción del frontend
# Usa Node.js para compilar React + Tailwind con Vite
FROM node:24-alpine AS builder

# Instalar pnpm globalmente
RUN npm install -g pnpm

WORKDIR /app

# Copiar dependencias primero para aprovechar caché de Docker
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Copiar el resto del código y compilar
COPY . .
RUN pnpm build

# Etapa 2: servidor de producción
# Nginx sirve los archivos compilados y hace proxy hacia la API
FROM nginx:alpine

# Copiar archivos compilados de la etapa anterior
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar configuración personalizada de Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
