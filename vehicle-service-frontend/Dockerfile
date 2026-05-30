# ── Stage 1: build Angular ────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build -- --configuration production

# ── Stage 2: serve with Nginx ─────────────────────────────────────────────────
FROM nginx:1.25-alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf

# Angular 17+ output goes to dist/<project>/browser
COPY --from=builder /app/dist/vehicle-service-frontend/browser /usr/share/nginx/html

EXPOSE 80
