# IoT Maintenance Insight Dashboard

> An application that ingests manufacturing sensor data, runs an AI-powered risk analysis workflow, and surfaces maintenance predictions on a live dashboard.

[![CI](https://github.com/sanjeevmax6/iot_dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/sanjeevmax6/iot_dashboard/actions/workflows/ci.yml)
[![CD](https://github.com/sanjeevmax6/iot_dashboard/actions/workflows/cd.yml/badge.svg)](https://github.com/sanjeevmax6/iot_dashboard/actions/workflows/cd.yml)

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Tech Stack](#tech-stack)
3. [Local Setup](#local-setup)
4. [AWS Deployment via GitHub Actions](#aws-deployment-via-github-actions)
5. [Architecture](#architecture)
6. [How the AI Works](#how-the-ai-works)
7. [File Structure](#file-structure)
8. [API Reference](#api-reference)
9. [Troubleshooting](#troubleshooting)

---

## What It Does

1. **Ingests** manufacturing floor sensor logs (temperature, vibration, status) from a CSV upload
2. **Runs** an LLM-powered risk analysis workflow (LangGraph, AWS Bedrock) to identify the top at-risk machines
3. **Validates** AI output with a two-stage schema + logic contradiction checker — retries automatically on failure
4. **Displays** raw logs, AI-generated machine health cards, and sensor time-series charts on a live dashboard
5. **Answers** follow-up questions about fleet health via an SSE-streaming chat interface

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.12), SQLAlchemy async, aiosqlite |
| AI Workflow | LangGraph, LangChain, AWS Bedrock (Amazon Nova Lite) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, Recharts |
| Containerisation | Docker, Docker Compose, Nginx |
| Infrastructure | AWS CDK (TypeScript) |
| Compute | AWS ECS Fargate |
| CDN / Storage | CloudFront + S3 |
| Registry | Amazon ECR |
| Networking | VPC, ALB, NAT Gateway |
| Secrets | AWS Secrets Manager |
| CI/CD | GitHub Actions |

---

## Local Setup

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- An OpenAI API key **or** AWS credentials with Bedrock access

### 1. Clone the repo

```bash
git clone https://github.com/sanjeevmax6/iot_dashboard.git
cd iot_dashboard
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set the following:

```env
# Choose your LLM provider
LLM_PROVIDER=openai

# If using OpenAI (recommended for local dev)
OPENAI_API_KEY=sk-...

# If using Bedrock instead
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# BEDROCK_REGION=us-east-1
# BEDROCK_MODEL_ID=us.amazon.nova-lite-v1:0
```

### 3. Start the full stack

```bash
docker compose -f infra/docker-compose.yml up --build
```

This starts three containers:
- `backend` — FastAPI on port 8000
- `frontend` — React (served via Nginx)
- `nginx` — reverse proxy on port 80, routes `/api/*` to backend

Open the app at **http://localhost**

### 4. Load sample data

Either use the **Ingest CSV** button in the dashboard, or run:

```bash
curl -X POST http://localhost/api/logs/ingest \
  -F "file=@assets/manufacturing_floor_logs_1000.csv"
```

Then click **Analyze Fleet Health** to trigger the AI analysis.

### 5. Run tests

```bash
# Backend (requires Python 3.12)
cd backend
pip install -r requirements.txt
pytest --cov=app --cov=agent

# Frontend
cd frontend
npm install
npm test
```

### Environment Variables Reference

| Variable | Description | Default |
|---|---|---|
| `LLM_PROVIDER` | `openai` or `bedrock` | `openai` |
| `OPENAI_API_KEY` | OpenAI secret key | — |
| `OPENAI_MODEL` | OpenAI model name | `gpt-4o-mini` |
| `BEDROCK_REGION` | AWS region | `us-east-1` |
| `BEDROCK_MODEL_ID` | Bedrock inference profile ID | `us.amazon.nova-lite-v1:0` |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite+aiosqlite:///./iot_dashboard.db` |
| `MAX_AI_RETRIES` | LLM validation retry limit | `3` |
| `TOP_AT_RISK_COUNT` | Machines to return from analysis | `3` |

---

## AWS Deployment via GitHub Actions

The entire AWS infrastructure is managed with CDK and deployed with a single button click. No local AWS tools required.

### Option A — Fork and deploy (recommended for evaluators)

1. **Fork** this repository to your GitHub account

2. **Add three GitHub Secrets** (Settings → Secrets and variables → Actions → New repository secret):

   | Secret name | Value |
   |---|---|
   | `AWS_ACCESS_KEY_ID` | Your IAM user access key |
   | `AWS_SECRET_ACCESS_KEY` | Your IAM user secret key |
   | `AWS_ACCOUNT_ID` | Your 12-digit AWS account number |

   The IAM user needs these permissions: `AdministratorAccess` (or a scoped policy covering CloudFormation, ECS, ECR, S3, CloudFront, Bedrock, IAM, VPC, Secrets Manager).

3. **Run the deploy workflow**:
   - Go to **Actions → Deploy IoT Dashboard → Run workflow → Run workflow**
   - The workflow takes ~10 minutes on a fresh account

4. **Get the app URL**:
   - When the workflow finishes, open the run summary — the CloudFront URL is printed there
   - Example: `https://d1abc123xyz.cloudfront.net`

5. **Tear everything down** when done:
   - Go to **Actions → Destroy IoT Dashboard → Run workflow → Run workflow**
   - All AWS resources are deleted; no charges continue after this

### GitHub Actions Workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | Push / PR to `main` | Lint, type-check, test (backend + frontend) |
| `deploy.yml` | Manual (`workflow_dispatch`) | Full from-scratch deploy of all AWS resources |
| `cd.yml` | PR merged to `main` | Rebuilds and redeploys backend image + frontend on existing infrastructure |
| `destroy.yml` | Manual (`workflow_dispatch`) | Tears down all AWS resources |

### Continuous Deployment — what happens on every PR merge to `main`

`cd.yml` runs automatically whenever a pull request is merged into `main`. It runs two jobs in parallel:

**Backend job:**
1. Builds a new Docker image tagged with the commit SHA and `latest`
2. Pushes both tags to ECR
3. Calls `aws ecs update-service --force-new-deployment` — ECS spins up a new Fargate task with the fresh image and drains the old one
4. Waits for the service to reach a stable state before the job completes

**Frontend job:**
1. Runs `npm ci && npm run build`
2. Syncs the `dist/` output to the S3 bucket (`--delete` removes stale files)
3. Issues a CloudFront `/*` cache invalidation so users get the latest build immediately

> **Note on the database:** ECS Fargate tasks have an ephemeral filesystem — each new deployment starts a fresh container with an empty SQLite database. For this demo, sensor data is re-ingested from the CSV after each deploy. In a production setup this would be replaced by an EFS-mounted volume or RDS instance.

---

## Architecture

### Production (AWS)

```
  Browser
     │
     ▼
┌─────────────┐
│  CloudFront │  CDN — serves React SPA from S3, proxies /api/* to ALB
└──────┬──────┘
       │ /api/*
       ▼
┌─────────────┐
│     ALB     │  Application Load Balancer (public subnet)
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│   ECS Fargate (private)     │
│  FastAPI + LangGraph agent  │  512 MB / 0.25 vCPU
└──────┬──────────────────────┘
       │
       ├──▶  SQLite (ephemeral, in-container)
       │
       └──▶  AWS Bedrock
              Amazon Nova Lite (us.amazon.nova-lite-v1:0)
              Inference profile — no Marketplace subscription needed

S3 Bucket  ◀──  React build artifacts (served via CloudFront OAC)
ECR        ◀──  Backend Docker image
Secrets Manager  ◀──  OpenAI API key (optional, injected at runtime)
```

### Key design decisions

| Decision | Rationale |
|---|---|
| Fargate over EC2 | No capacity planning needed; auto-scales to zero when idle |
| CloudFront + S3 for frontend | Static hosting at CDN edge; same origin as API avoids CORS complexity |
| ALB not public-facing directly | CloudFront sits in front, so browser requests never hit the ALB URL directly |
| Amazon Nova Lite as default model | No AWS Marketplace subscription required — works on any fresh AWS account out of the box |
| SQLite (not RDS) | Acceptable for this scope; resets on each deploy which is fine for a demo |
| NAT Gateway in VPC | Fargate tasks in private subnets need outbound internet access to reach Bedrock |

### Local (Docker Compose)

```
  Browser
     │
     ▼
┌─────────────┐
│    Nginx    │  :80 — reverse proxy
└──────┬──────┘
       ├──▶  /api/*  ──▶  FastAPI (backend:8000)
       └──▶  /*      ──▶  React build (frontend:80)
```

---

## How the AI Works

The AI system has two independent components: a **batch analysis workflow** and a **streaming chat interface**.

### 1. Fleet Analysis Workflow (LangGraph)

When you click **Analyze Fleet Health**, this pipeline runs:

```
                    ┌─────────────┐
                    │  Summarizer │
                    │  (SQL agg)  │  Aggregates per-machine stats from DB:
                    └──────┬──────┘  error rate, avg/max temp & vibration
                           │
                           ▼
                    ┌─────────────┐
              ┌────▶│  invoke_llm │  Calls Bedrock with structured output.
              │     │             │  The LLM must return a typed AnalysisOutput
              │     └──────┬──────┘  (Pydantic schema injected as a tool).
              │            │
              │            ▼
              │     ┌─────────────┐  Stage 1: Pydantic schema validation
              │     │  validate   │  Stage 2: Logic contradiction checks:
              │     │             │   - risk_score within bounds for risk_level
  retry ◀─────┤     │             │   - no fabricated machine IDs
  (up to 3x)  │     │             │   - descending risk score order
              │     │             │   - high-risk machines must have affected sensors
              │     └──────┬──────┘
              │            │  errors?
              └────────────┘
                           │  clean
                           ▼
                    ┌─────────────┐
                    │  summarize  │  Sets error_state if all retries failed
                    └─────────────┘
```

**Why the validation layer?** LLMs occasionally hallucinate machine IDs, assign a `risk_score` that contradicts the stated `risk_level`, or return results in the wrong order. Rather than silently accepting bad data, the validator catches these contradictions and feeds the exact errors back to the LLM as correction instructions, retrying up to `MAX_AI_RETRIES` times.

### 2. Intent Guard

Before every chat message is processed, a lightweight classifier call checks whether the message is on-topic (fleet/machine domain). Off-topic messages (weather, general knowledge, etc.) are refused with a canned message. This uses the same LLM but without tool calling — just a simple `ON_TOPIC` / `OFF_TOPIC` classification.

### 3. Streaming Chat (SSE)

The chat interface uses Server-Sent Events for token streaming:

```
Browser  ──POST /api/analysis/chat/stream──▶  FastAPI
                                                 │
                                          ┌──────┴──────┐
                                          │  classify   │  intent guard
                                          │  intent     │
                                          └──────┬──────┘
                                                 │ ON_TOPIC
                                          ┌──────┴──────┐
                                          │ stream_chat │  LangChain RunnableWithMessageHistory
                                          │             │  Bedrock ConverseStream API
                                          └──────┬──────┘
                                                 │
         ◀── SSE: {"type":"thinking_token"} ─────┘  (streamed as tokens arrive)
         ◀── SSE: {"type":"done"}                   (signals completion)
```

Session memory (conversation history) is held in-process per `session_id`. It resets on server restart — acceptable for this scope.

### 4. LLM Provider switching

The `LLM_PROVIDER` env var switches between OpenAI (local dev) and Bedrock (production) at startup. Both providers go through the same LangGraph graph — only the underlying `ChatModel` instance changes.

```
LLM_PROVIDER=openai   → ChatOpenAI  (gpt-4o-mini by default)
LLM_PROVIDER=bedrock  → ChatBedrock (us.amazon.nova-lite-v1:0 by default)
```

To use Claude on Bedrock instead of Nova, enable model access in the Bedrock console and set:
```env
BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
```

---

## File Structure

```
iot_dashboard/
│
├── backend/                        FastAPI application + AI agent
│   ├── app/
│   │   ├── api/routes/             HTTP endpoints
│   │   │   ├── analysis.py         POST /api/analysis/run, GET /api/analysis/status
│   │   │   ├── chat.py             POST /api/analysis/chat/stream (SSE)
│   │   │   ├── logs.py             GET /api/logs, POST /api/logs/ingest
│   │   │   ├── machines.py         GET /api/machines
│   │   │   └── data.py             GET /api/data (sensor time-series)
│   │   ├── models/                 SQLAlchemy ORM models
│   │   ├── schemas/                Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── ingestion.py        CSV parsing + bulk DB insert
│   │   │   └── summarizer.py       SQL aggregation for AI input
│   │   ├── core/
│   │   │   ├── config.py           Settings (reads from .env)
│   │   │   └── database.py         Async SQLAlchemy engine setup
│   │   └── main.py                 FastAPI app, CORS, lifespan
│   │
│   ├── agent/                      LangGraph AI workflow
│   │   ├── graph.py                LangGraph state machine (invoke → validate → summarize)
│   │   ├── schemas.py              Pydantic output types (AnalysisOutput, MachineRisk)
│   │   ├── validator.py            Stage 2 logic contradiction checker
│   │   ├── prompts.py              System prompts + user prompt builder
│   │   ├── chat.py                 Streaming chat, intent guard, session memory
│   │   └── llm_rerouter.py         Provider switch (OpenAI ↔ Bedrock)
│   │
│   ├── tests/                      Pytest test suite (>80% coverage)
│   ├── Dockerfile                  Multi-stage build (builder + slim runtime)
│   └── requirements.txt
│
├── frontend/                       React + TypeScript SPA
│   ├── src/
│   │   ├── App.tsx                 Root component + routing
│   │   └── ...                     Pages, components, hooks, API clients
│   ├── Dockerfile                  Nginx-served production build
│   └── package.json
│
├── infra/
│   ├── docker-compose.yml          Local dev stack (backend + frontend + nginx)
│   ├── nginx/nginx.conf            Local reverse proxy config
│   └── cdk/                        AWS CDK (TypeScript)
│       ├── app.ts                  Stack entry point
│       └── lib/
│           ├── vpc-stack.ts        VPC, subnets, NAT Gateway
│           ├── ecr-stack.ts        ECR repository
│           ├── ecs-stack.ts        Fargate service, ALB, IAM roles, Secrets Manager
│           └── frontend-stack.ts   S3 bucket, CloudFront distribution (OAC)
│
├── .github/workflows/
│   ├── ci.yml                      Lint + test on every push/PR
│   ├── deploy.yml                  One-click full AWS deploy (manual trigger)
│   ├── cd.yml                      Update backend + frontend on PR merge to main
│   └── destroy.yml                 Tear down all AWS resources (manual trigger)
│
└── assets/
    └── manufacturing_floor_logs_1000.csv   Sample sensor data (1,000 rows)
```

---

## API Reference

Full interactive docs available at `http://localhost/api/docs` when running locally.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/logs/ingest` | Upload CSV sensor data |
| `GET` | `/api/logs` | Paginated log listing with filters |
| `GET` | `/api/machines` | List all machine IDs |
| `GET` | `/api/data` | Sensor time-series for charts |
| `POST` | `/api/analysis/run` | Trigger background AI analysis job |
| `GET` | `/api/analysis/status/{job_id}` | Poll analysis job status |
| `GET` | `/api/analysis/latest` | Get most recent completed analysis |
| `POST` | `/api/analysis/chat/stream` | SSE streaming chat |

---

## Troubleshooting

### ECS Circuit Breaker triggered on deploy

**Symptom:** `ECS Deployment Circuit Breaker was triggered` in CloudFormation events.

**Cause:** ECS tried to start tasks before a valid Docker image existed in ECR, or the image was built for the wrong CPU architecture.

**Fix:** The `deploy.yml` workflow handles this automatically by:
1. Deploying ECR before building the image
2. Building with `--platform linux/amd64` (required for Fargate)
3. Detecting and deleting `ROLLBACK_COMPLETE` stacks before retrying

If deploying manually, always follow this order: deploy ECR → push image → deploy ECS.

---

### CDK bootstrap fails with "No bucket named cdk-hnb659fds-assets-..."

**Symptom:** `Failed to publish one or more assets. No bucket named 'cdk-hnb659fds-assets-ACCOUNT-REGION'`

**Cause:** The CDKToolkit CloudFormation stack exists but its S3 bucket was manually deleted. CDK bootstrap sees "no changes" and skips recreating the bucket (stack drift).

**Fix:**
```bash
aws cloudformation delete-stack --stack-name CDKToolkit --region us-east-1
aws cloudformation wait stack-delete-complete --stack-name CDKToolkit --region us-east-1
npx cdk bootstrap aws://ACCOUNT_ID/us-east-1
```

The `deploy.yml` workflow detects and handles this automatically.

---

### Docker image platform mismatch

**Symptom:** `image Manifest does not contain descriptor matching platform 'linux/amd64'`

**Cause:** The image was built on Apple Silicon (arm64) without specifying the target platform. Fargate uses x86_64.

**Fix:** Always build with the platform flag:
```bash
docker build --platform linux/amd64 -t my-image ./backend
```

---

### Bedrock model access denied

**Symptom:** `AccessDeniedException: not authorized to perform bedrock:InvokeModel`

**Two possible causes:**

1. **Model not enabled** — Anthropic models require a one-time Marketplace subscription. Go to **AWS Console → Bedrock → Model access** and enable the model. Amazon Nova models (the default) do not require this.

2. **Missing IAM action** — Streaming chat uses `bedrock:InvokeModelWithResponseStream`, which is separate from `bedrock:InvokeModel`. Both are granted in `ecs-stack.ts`.

---

### Bedrock tool description validation error

**Symptom:** `Parameter validation failed: Invalid length for parameter toolConfig.tools[0].toolSpec.description, value: 0, valid min length: 1`

**Cause:** Amazon Nova (and some other Bedrock models) strictly require non-empty `description` fields on every Pydantic field and class used with `with_structured_output`. OpenAI is more lenient.

**Fix:** Ensure all Pydantic models used as structured output have:
- A class docstring (becomes `toolSpec.description`)
- `Field(description="...")` on every field (becomes parameter descriptions)

This is already applied in `agent/schemas.py`.

---

### Chat streaming produces garbled or no output

**Symptom:** Chat tokens appear as `[object Object]` or chat silently fails.

**Cause:** Amazon Nova returns `chunk.content` as a list of content blocks (e.g. `[{"type": "text", "text": "..."}]`) rather than a plain string. OpenAI returns a plain string.

**Fix:** The `stream_chat` function in `agent/chat.py` handles both formats by checking `isinstance(raw, list)` and extracting text from each block accordingly.

---

### Stack stuck in ROLLBACK_COMPLETE

**Symptom:** CDK deploy fails with `Stack is in ROLLBACK_COMPLETE state and cannot be updated`.

**Fix:**
```bash
aws cloudformation delete-stack --stack-name IotDashboardEcs --region us-east-1
aws cloudformation wait stack-delete-complete --stack-name IotDashboardEcs --region us-east-1
# Then re-run the deploy
```

The `deploy.yml` workflow detects and handles this automatically.

---

### Frontend shows AccessDenied XML

**Symptom:** Visiting the CloudFront URL shows `<Error><Code>AccessDenied</Code>` XML.

**Cause:** The S3 bucket is empty — the React app was never built and synced.

**Fix:** Run the frontend deploy step:
```bash
cd frontend && npm ci && npm run build
aws s3 sync dist/ s3://YOUR_BUCKET_NAME --delete
aws cloudfront create-invalidation --distribution-id YOUR_CF_ID --paths "/*"
```

Bucket name and CloudFront ID are in the `IotDashboardFrontend` stack outputs:
```bash
aws cloudformation describe-stacks --stack-name IotDashboardFrontend \
  --query 'Stacks[0].Outputs' --output table
```
