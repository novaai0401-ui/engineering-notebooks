FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastmcp==4.0.5 && useradd --uid 10001 --create-home learner
COPY server.py /app/server.py
USER learner
ENV MCP_HOST=0.0.0.0 MCP_PORT=8093
EXPOSE 8093
CMD ["python","server.py"]
