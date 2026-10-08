FROM python:3.12.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY adapter/ /app/adapter/
COPY api/ /app/api/
USER 10001:10001
CMD ["python", "/app/adapter/server.py"]
