FROM node:18 AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/ ./
RUN npm install && npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=frontend-build /app/dist /app/frontend/dist
COPY . .
EXPOSE 7860
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
