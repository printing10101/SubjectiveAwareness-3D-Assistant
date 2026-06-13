# syntax=docker/dockerfile:1.7

# ============================================================
# Stage 1: Build the Vue 3 + Vite production assets
# ============================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first to leverage Docker layer caching.
# package-lock.json guarantees reproducible installs (npm ci).
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Copy the rest of the source code and build for production.
COPY . .
RUN npm run build

# ============================================================
# Stage 2: Serve the built assets with Nginx
# ============================================================
FROM nginx:alpine AS runtime

# Remove the default Nginx welcome page so our config is the only site.
RUN rm -f /etc/nginx/conf.d/default.conf

# Install curl for the HEALTHCHECK (nginx:alpine ships busybox wget only).
RUN apk add --no-cache curl

# Copy the custom Nginx configuration (SPA routing, /api proxy, gzip, cache).
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built static assets from the build stage.
COPY --from=builder /app/dist /usr/share/nginx/html

# Grant the nginx user ownership of the writable runtime directories.
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx

EXPOSE 80

# Health check: verify Nginx is responding on port 80.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
