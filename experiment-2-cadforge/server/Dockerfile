FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml openenv.yaml README.md ./
COPY data/cad_tasks.json ./data/cad_tasks.json
COPY data/generated-assets ./data/generated-assets
COPY data/reference-metrics ./data/reference-metrics
COPY python_tools ./python_tools
COPY server ./server

RUN uv pip install --system .

ENV PYTHONPATH=/app/python_tools
ENV ENABLE_WEB_INTERFACE=false

EXPOSE 8000

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
