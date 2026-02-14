# Multi-stage build for React + Vite frontend

# Stage 1: Build
FROM node:18-alpine AS builder

WORKDIR /app

# Build arguments for Vite environment variables
ARG VITE_GOOGLE_CLIENT_ID
ARG VITE_API_URL

# Set environment variables for build
ENV VITE_GOOGLE_CLIENT_ID=${VITE_GOOGLE_CLIENT_ID}
ENV VITE_API_URL=${VITE_API_URL}

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies (use npm install if no lock file exists)
RUN npm install

# Copy source code (explicitly copy to ensure all files are included)
# Copy config files first
COPY vite.config.ts tsconfig.json tsconfig.node.json ./
COPY tailwind.config.js postcss.config.js ./
COPY index.html ./

# Copy entire src directory (including all subdirectories like lib/)
# Use explicit COPY to ensure all files are included
COPY src ./src

# Debug: Verify what was copied - show BEFORE the verification step
RUN echo "==========================================" && \
    echo "DEBUG: Checking what was copied to ./src" && \
    echo "==========================================" && \
    echo "" && \
    echo "=== Current directory ===" && \
    pwd && \
    echo "" && \
    echo "=== src directory exists? ===" && \
    ([ -d ./src ] && echo "YES" || echo "NO") && \
    echo "" && \
    echo "=== src directory listing ===" && \
    ls -la ./src/ 2>&1 || echo "src directory not found!" && \
    echo "" && \
    echo "=== lib directory exists? ===" && \
    ([ -d ./src/lib ] && echo "YES" || echo "NO") && \
    echo "" && \
    echo "=== Checking lib directory (if exists) ===" && \
    (ls -la ./src/lib/ 2>&1 || echo "lib directory not found!") && \
    echo "" && \
    echo "=== Full src directory tree (all files) ===" && \
    find ./src -type f 2>&1 | head -50 || echo "No files found in src!" && \
    echo "" && \
    echo "=== Full src directory tree (all directories) ===" && \
    find ./src -type d 2>&1 | head -30 || echo "No directories found in src!"

# Verify critical files exist before build
RUN test -f ./src/lib/strategyTemplates.ts && \
    test -f ./src/lib/utils.ts && \
    echo "✓ Critical files verified" || \
    (echo "✗ Missing critical files!" && \
     echo "Current working directory: $(pwd)" && \
     echo "src directory exists: $([ -d ./src ] && echo 'YES' || echo 'NO')" && \
     echo "lib directory exists: $([ -d ./src/lib ] && echo 'YES' || echo 'NO')" && \
     exit 1)

# Build the application
RUN npm run build

# Stage 2: Production
FROM nginx:alpine

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# SPA + cache control: index.html never cached (avoids stale asset hashes → MIME errors on refresh). /assets/ 404 → plain 404, not HTML.
RUN echo 'server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location = /index.html { \
        add_header Cache-Control "no-cache, no-store, must-revalidate"; \
        add_header Pragma "no-cache"; \
        add_header Expires "0"; \
    } \
    location /assets/ { \
        try_files $uri @assets_404; \
        add_header Cache-Control "public, max-age=31536000, immutable"; \
    } \
    location @assets_404 { \
        default_type text/plain; \
        return 404 "Not Found"; \
    } \
    location / { \
        try_files $uri $uri/ /index.html; \
        add_header Cache-Control "no-cache, no-store, must-revalidate"; \
        add_header Pragma "no-cache"; \
        add_header Expires "0"; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

