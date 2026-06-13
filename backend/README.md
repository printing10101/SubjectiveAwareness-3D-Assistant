# Case Analysis Backend

FastAPI backend service for three-dimensional criminal case analysis powered by Ollama LLM.

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) installed and running
- `deepseek-r1:7b` model pulled via `ollama pull deepseek-r1:7b`

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy and configure environment (optional)
cp .env.example .env

# 3. Start the server
python main.py

# Or with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

| Method | Path            | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | `/health`       | Health check with Ollama status      |
| POST   | `/api/analyze`  | Analyze a case text (3D analysis)   |
| GET    | `/docs`         | Swagger UI (auto-generated)          |
| GET    | `/redoc`        | ReDoc documentation                  |

## Request Example

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"case_text": "嫌疑人声称案发时在家睡觉，但监控显示其车辆出现在案发现场附近..."}'
```

## Configuration

| Environment Variable | Default                    | Description                |
|----------------------|----------------------------|----------------------------|
| `OLLAMA_BASE_URL`    | `http://localhost:11434`   | Ollama service URL         |
| `OLLAMA_MODEL`       | `deepseek-r1:7b`           | LLM model to use           |
| `SERVER_HOST`        | `0.0.0.0`                  | Server bind address        |
| `SERVER_PORT`        | `8000`                     | Server port                |
