FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY benchmark ./benchmark
COPY results ./results
COPY --from=frontend /app/frontend/dist ./frontend/dist
COPY .env.example ./.env.example
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["sh", "-c", "python -m backend.whybase.seed.load && uvicorn backend.whybase.main:app --host 0.0.0.0 --port 8000"]
