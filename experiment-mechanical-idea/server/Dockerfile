FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml openenv.yaml README.md ./
COPY python_tools ./python_tools
COPY server ./server

RUN uv pip install --system .

ENV PYTHONPATH=/app/python_tools
ENV ENABLE_WEB_INTERFACE=false

EXPOSE 8000

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]

