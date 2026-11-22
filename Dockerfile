# ---------- 1) Compilar la página (Astro) ----------
FROM node:22-slim AS web
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY astro.config.mjs svelte.config.js tsconfig.json ./
COPY public ./public
COPY src ./src
RUN npm run build

# ---------- 2) Servidor (FastAPI) + página compilada ----------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=web /web/dist /app/dist

# Render usa la variable PORT; en otros lugares, el 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
