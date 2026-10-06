# Сборка из корня lab19_Nenad: docker build -f notification_service/Dockerfile .
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common ./common
COPY notification_service ./notification_service
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "notification_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
