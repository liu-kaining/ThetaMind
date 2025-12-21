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

# Copy source code - use . to copy everything, but explicitly ensure lib is included
COPY src ./src

# Ensure public directory exists (Vite may need it)
RUN mkdir -p ./public

# Verify critical files exist before build
RUN test -f ./src/lib/strategyTemplates.ts && \
    test -f ./src/lib/utils.ts && \
    echo "✓ Critical files verified" || \
    (echo "✗ Missing critical files!" && \
     ls -la ./src/lib/ 2>&1 && \
     find ./src -name "*strategyTemplates*" 2>&1 && \
     exit 1)

# Build the application
RUN npm run build

# Stage 2: Production
FROM nginx:alpine

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration (optional, for SPA routing)
RUN echo 'server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

