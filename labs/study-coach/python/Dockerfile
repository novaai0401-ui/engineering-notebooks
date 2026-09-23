FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.135.2 uvicorn==0.42.0 scikit-learn==1.8.0 httpx==0.28.1 prometheus-client==0.25.0 opentelemetry-sdk==1.41.1 opentelemetry-exporter-otlp-proto-http==1.41.1 && useradd --uid 10001 --create-home learner
COPY coach_ai.py ollama_agent.py telemetry.py ./
USER learner
EXPOSE 8092
CMD ["python","-m","uvicorn","coach_ai:app","--host","0.0.0.0","--port","8092"]
