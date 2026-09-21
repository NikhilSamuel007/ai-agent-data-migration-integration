FROM node:22-bookworm-slim AS build
WORKDIR /frontend
RUN npm install --global pnpm@11.19.0
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    FRONTEND_PORT=3000 \
    API_BASE_URL=http://localhost:8000
WORKDIR /app
RUN groupadd --gid 10001 relay \
    && useradd --uid 10001 --gid relay --create-home relay
COPY --chown=relay:relay server.py ./
COPY --from=build --chown=relay:relay /frontend/dist/ ./dist/
USER relay
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3000/', timeout=3).close()"
CMD ["python", "server.py"]
