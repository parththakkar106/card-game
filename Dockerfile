# Build the React pages in a Node image, then copy only the output into the
# Python image. The final image has no Node and no node_modules.
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
COPY --from=web /web/dist web/dist
EXPOSE 8000
# Bind to all interfaces so Caddy can reach the app from another container.
# Keep one worker: rooms live in this process's memory.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
