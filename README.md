# IoT Maintenance Insight Dashboard

> A production-grade full-stack application that ingests manufacturing sensor data, runs an AI-powered risk analysis workflow, and surfaces maintenance predictions on a live dashboard.

[![CI](https://github.com/sanjeevmax6/iot_dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/sanjeevmax6/iot_dashboard/actions/workflows/ci.yml)
[![CD](https://github.com/sanjeevmax6/iot_dashboard/actions/workflows/cd.yml/badge.svg)](https://github.com/sanjeevmax6/iot_dashboard/actions/workflows/cd.yml)

---

## What It Does

1. Ingests 1,000+ manufacturing floor sensor logs (temperature, vibration, status) from a CSV
2. Runs an LLM-powered analysis workflow (LangGraph + OpenAI / AWS Bedrock) to identify the top 3 at-risk machines
3. Validates AI output with a two-stage schema + logic contradiction checker
4. Displays raw logs and AI-generated health cards on a real-time dashboard

---

## Features

- **Fleet Dashboard** — paginated log table with filters by machine, status, and date range
- **AI Trends Page** — machine health cards with risk level, score, affected sensors, and recommended action
- **Sensor Charts** — dual-axis time-series charts (temperature + vibration) with error/warning overlays
- **Validation Layer** — rejects malformed or logically contradictory LLM responses; retries automatically
- **Provider-Agnostic AI** — OpenAI (local dev) or AWS Bedrock (production) via a single config switch
- **One-Command Local Start** — `docker compose up` runs the full stack

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.12), SQLAlchemy, Alembic |
| AI Workflow | LangGraph, LangChain (OpenAI / AWS Bedrock) |
| Database | SQLite (dev), EFS-backed SQLite (prod) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Charts | Recharts |
| Containers | Docker, Docker Compose, Nginx |
| Cloud | AWS ECS Fargate, S3 + CloudFront, Bedrock, CDK |
| CI/CD | GitHub Actions |

---

## Getting Started

### Prerequisites

- Docker + Docker Compose
- An OpenAI API key (for local dev)

### Local Development

```bash
# Clone the repo
git clone https://github.com/sanjeevmax6/iot_dashboard.git
cd iot_dashboard

# Copy and fill in environment variables
cp .env.example .env
# Edit .env: set OPENAI_API_KEY=sk-...

# Start everything
docker compose -f infra/docker-compose.yml up

# Open the app
open http://localhost
```

The first time, ingest the sample data via the dashboard's **Ingest CSV** button or:

```bash
curl -X POST http://localhost/api/logs/ingest \
  -F "file=@assets/manufacturing_floor_logs_1000.csv"
```

### Running Tests

```bash
# Backend
cd backend
pip install -r requirements-dev.txt
pytest --cov=app

# Frontend
cd frontend
npm install
npm test
```

---

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Description | Default |
|---|---|---|
| `LLM_PROVIDER` | `openai` or `bedrock` | `openai` |
| `OPENAI_API_KEY` | OpenAI secret key | — |
| `OPENAI_MODEL` | Model name | `gpt-4o-mini` |
| `BEDROCK_REGION` | AWS region for Bedrock | `us-east-1` |
| `BEDROCK_MODEL_ID` | Bedrock model ID | `anthropic.claude-haiku-4-5-...` |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite+aiosqlite:///./iot_dashboard.db` |
| `MAX_AI_RETRIES` | Validation retry limit | `3` |

---

## Deployment (AWS)

Infrastructure is managed with AWS CDK. One-time setup:

```bash
cd infra/cdk
npm install
npx cdk bootstrap aws://ACCOUNT_ID/REGION
npx cdk deploy --all
```

After that, every merge to `main` triggers a full deploy via GitHub Actions (see `.github/workflows/cd.yml`).

Required GitHub Actions secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_ACCOUNT_ID`.

---

## Project Structure

```
iot_dashboard/
├── backend/         FastAPI app, LangGraph workflow, DB models
├── frontend/        React + TypeScript dashboard
├── infra/           Docker Compose, Nginx, AWS CDK stacks
├── .github/         CI/CD workflows
├── assets/          Sample data + assignment brief
├── PLANNING.md      Architecture decisions and build plan
└── README_AI.md     AI usage log (prompts, fixes, verification)
```

---

## API Docs

When running locally, OpenAPI docs are available at:

```
http://localhost/api/docs
```

---

## License

MIT
