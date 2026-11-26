FROM python:3.12-slim
WORKDIR /app
COPY app.py core.py simulator.py integrations.py ./
COPY static ./static
COPY docs/openapi.json ./docs/openapi.json
RUN useradd -m bovi && mkdir -p /app/data && chown bovi:bovi /app/data
USER bovi
ENV PORT=8000 BOVIFLOW_DB=/app/data/demo.db PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "app.py", "--host", "0.0.0.0"]
