# IoT Maintenance Insight Dashboard — Technical Planning Document

> This is the internal planning and architecture document. It contains all design decisions, rationale, trade-offs, and the step-by-step build order. The README.md is the public-facing project overview.

---

## 1. Problem Summary

Build a production-grade **Maintenance Predictor** that:
1. Ingests any CSV of manufacturing floor sensor logs (timestamp, machine_id, temperature, vibration, status)
2. Uses an LLM-powered workflow to identify the top 3 at-risk machines from whatever data is present
3. Validates AI output with schema enforcement + logic contradiction checks
4. Stores results and serves them via a REST API
5. Displays findings on a live, clean dashboard

The system is data-agnostic — it works with any number of machines, any time range, and any volume of logs. A sample dataset (1,000 rows, 8 machines, 4 days) is used.

---

## 2. Key Decisions & Reasoning

### 2.1 Is the LLM Task "Simple"?

Yes — unambiguously. The LLM receives ~8 pre-aggregated JSON objects (~200 input tokens total) and returns a ranked list of 3 machines (~150 output tokens). There is no:
- Multi-document cross-referencing
- Multi-hop reasoning
- Ambiguous language to interpret
- Creative generation

This is a **structured data classification task**. Any modern small model handles it accurately. Extended reasoning (what makes Claude Sonnet appear "slow" for simple tasks) would be pure overhead here. The right model tier is **fast small models** (Claude Haiku, GPT-4o-mini).

### 2.2 LLM Provider Strategy: Dual-Provider via LangChain

| Environment | Provider | Model | Why |
|---|---|---|---|
| Local dev | **OpenAI** | `gpt-4o-mini` | Key already available, native `response_format` JSON support, cheapest (~$0.00008/call) |
| Production (AWS) | **AWS Bedrock** | `anthropic.claude-haiku-4-5` | Data stays in VPC, no outbound API calls, CDK-native IAM auth, NYISO precedent, Bedrock is managed |

**Why not Bedrock for local dev too?** Bedrock requires AWS credentials, a region, and model access approvals — more friction for first-run. OpenAI is one env var.

**Why not OpenAI for prod?** Manufacturing sensor data is potentially proprietary. Sending it to an external third-party API creates a data residency/compliance risk. Bedrock keeps all data within your AWS account with full VPC isolation.

**How to make both work:** LangChain's `BaseChatModel` abstraction — both providers implement `.invoke()` identically. A factory function reads `LLM_PROVIDER` from env and instantiates the right client. Zero code changes between environments.

```
LLM_PROVIDER=openai   → ChatOpenAI(model="gpt-4o-mini")
LLM_PROVIDER=bedrock  → ChatBedrock(model_id="anthropic.claude-haiku-4-5-20251001-v1:0")
```

### 2.3 LangGraph for the AI Workflow

LangGraph is the right tool here because the core AI workflow is a **state machine with conditional branching**:

```
[START]
   ↓
[aggregate]     — query DB, build per-machine stats dict
   ↓
[call_llm]      — invoke model with system prompt + summaries
   ↓
[validate]      — Pydantic schema check + logic contradiction check
   ↓
[router] ──── valid ────→ [persist] → [END]
    └──── invalid & retry_count < 3 ──→ [regenerate] → [validate] (loop)
    └──── exhausted retries ──────────→ [error_state] → [END]
```

Without LangGraph you hand-roll this as nested try/except with a counter. With LangGraph:
- State is typed (`TypedDict`)
- Each node is a pure function — independently unit-testable
- Conditional edges are explicit and readable
- LangSmith (LangChain's observability tool) gives traces for free

### 2.4 Validation Layer Design

Two-stage, both must pass:

**Stage 1 — Pydantic schema:**
- All required fields present and correct types
- `risk_level` ∈ `{high, medium, low}`
- `risk_score` ∈ `[0.0, 1.0]`
- `machine_id` exists in the database
- `affected_sensors` is a non-empty list

**Stage 2 — Logic contradictions (the hard part):**
- `risk_level == "high"` → `risk_score >= 0.7`
- `risk_level == "low"` → `risk_score <= 0.4`
- `risk_level == "high"` → `len(affected_sensors) >= 1`
- Each top-3 machine must have ≥ 1 warning or error in the actual DB (prevents hallucinated machine IDs)
- Risk scores must be strictly descending (rank 1 > rank 2 > rank 3)

On failure: append the specific contradiction message to the next prompt iteration. Max 3 retries. On exhaustion: store an error record and surface it in the UI.

---

## 3. Full Tech Stack

### Backend
| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.115.x | API framework |
| `uvicorn[standard]` | 0.30.x | ASGI server |
| `sqlalchemy[asyncio]` | 2.0.x | ORM |
| `aiosqlite` | 0.20.x | Async SQLite driver |
| `pydantic-settings` | 2.x | Env-based config |
| `langchain-core` | 0.3.x | LangChain base + message types |
| `langchain-openai` | 0.2.x | OpenAI provider |
| `langchain-aws` | 0.2.x | Bedrock provider |
| `langgraph` | 0.2.x | AI workflow graph |
| `python-multipart` | latest | File upload support |
| `structlog` | latest | Structured JSON logging |
| `pytest` + `pytest-asyncio` | latest | Test runner |
| `httpx` | latest | Async test client for FastAPI |
| `pytest-cov` | latest | Coverage reporting |
| `ruff` | latest | Lint + format |
| `mypy` | latest | Static type checking |

### Frontend
| Package | Version | Purpose |
|---|---|---|
| `react` + `react-dom` | 18.x | UI framework |
| `typescript` | 5.x | Type safety |
| `vite` | 5.x | Dev server + bundler |
| `@tanstack/react-query` | 5.x | Server state management |
| `react-router-dom` | 6.x | Client-side routing |
| `tailwindcss` | 3.x | Utility CSS |
| `shadcn/ui` | latest | Component library (built on Radix) |
| `recharts` | 2.x | Time-series charts |
| `lucide-react` | latest | Icon set |
| `date-fns` | 3.x | Date formatting |
| `sonner` | latest | Toast notifications |
| `clsx` + `tailwind-merge` | latest | Class merging (shadcn dep) |

### Frontend Dev/Test
| Package | Purpose |
|---|---|
| `vitest` | Fast unit test runner |
| `@testing-library/react` | Component tests |
| `@testing-library/user-event` | User interaction simulation |
| `msw` (Mock Service Worker) | API mocking in tests |
| `eslint` + `@typescript-eslint` | Lint |

### Infrastructure & Deployment
| Tool | Purpose |
|---|---|
| Docker + Docker Compose | Local container orchestration |
| Nginx | Reverse proxy (local + prod-like) |
| AWS CDK (TypeScript) | Infrastructure as code |
| AWS ECS Fargate | Backend container hosting |
| AWS ECR | Container image registry |
| AWS S3 + CloudFront | Frontend static hosting |
| AWS Bedrock | LLM inference (prod) |
| AWS Secrets Manager | API keys + DB credentials |
| AWS ALB | Load balancer for ECS |
| AWS VPC | Network isolation |
| GitHub Actions | CI/CD pipelines |

---

## 4. Repository Structure

```
iot_dashboard/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py                    # FastAPI dependencies (DB session, auth)
│   │   │   └── routes/
│   │   │       ├── logs.py                # POST /logs/ingest, GET /logs
│   │   │       ├── machines.py            # GET /machines, GET /machines/{id}
│   │   │       └── analysis.py            # POST /analysis/run, GET /analysis/latest, GET /analysis/history
│   │   ├── core/
│   │   │   ├── config.py                  # pydantic-settings: all env vars
│   │   │   └── database.py                # SQLAlchemy async engine + session factory
│   │   ├── models/
│   │   │   ├── log_entry.py               # ORM: sensor readings table
│   │   │   ├── machine.py                 # ORM: machines table
│   │   │   └── analysis_result.py         # ORM: AI analysis results table
│   │   ├── schemas/
│   │   │   ├── log_entry.py               # Pydantic I/O for logs
│   │   │   ├── machine.py                 # Pydantic I/O for machines
│   │   │   └── analysis.py                # Strict Pydantic schema for LLM output
│   │   ├── services/
│   │   │   ├── ingestion.py               # CSV parse + bulk DB upsert
│   │   │   └── summarizer.py              # DB query → per-machine aggregate stats
│   │   └── main.py                        # FastAPI app factory, CORS, lifespan
│   ├── agent/                             # AI layer — no FastAPI/DB knowledge
│   │   ├── __init__.py
│   │   ├── workflow.py                    # LangGraph graph: entry point for the backend
│   │   ├── llm.py                         # LangChain LLM factory (OpenAI/Bedrock)
│   │   ├── validator.py                   # Stage 1: Pydantic schema, Stage 2: logic checks
│   │   └── prompts.py                     # System + user prompt builders
│   ├── tests/
│   │   ├── conftest.py                    # Fixtures: in-memory DB, test client, mock LLM
│   │   ├── test_ingestion.py              # Unit: CSV parsing, deduplication
│   │   ├── test_summarizer.py             # Unit: aggregate stats calculation
│   │   ├── test_validator.py              # Unit: all agent validation paths (20+ cases)
│   │   ├── test_workflow.py               # Unit: LangGraph graph with mocked LLM
│   │   └── test_routes.py                 # Integration: all HTTP endpoints
│   ├── .env.example
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts                  # Typed fetch wrappers for all endpoints
│   │   ├── components/
│   │   │   ├── ui/                        # shadcn auto-generated primitives
│   │   │   ├── layout/
│   │   │   │   ├── Navbar.tsx
│   │   │   │   └── PageShell.tsx          # Consistent page wrapper
│   │   │   ├── LogsTable.tsx              # Virtualized paginated table
│   │   │   ├── MachineHealthCard.tsx      # AI risk summary card
│   │   │   ├── RiskBadge.tsx              # high/medium/low color badge
│   │   │   ├── SensorChart.tsx            # Recharts dual-axis time series
│   │   │   ├── FleetStatsBar.tsx          # Top summary row (4 KPI tiles)
│   │   │   └── AnalysisTrigger.tsx        # Run Analysis button + status
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx              # / — fleet overview + logs table
│   │   │   └── Trends.tsx                 # /trends — AI cards + charts
│   │   ├── hooks/
│   │   │   ├── useLogs.ts                 # React Query: fetch + filter logs
│   │   │   ├── useMachines.ts             # React Query: fetch machines
│   │   │   └── useAnalysis.ts             # React Query: trigger + poll analysis
│   │   ├── types/
│   │   │   └── index.ts                   # TypeScript types matching API schemas exactly
│   │   ├── lib/
│   │   │   └── utils.ts                   # clsx/tailwind-merge helpers
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── tests/
│   │   ├── setup.ts                       # MSW server setup
│   │   ├── mocks/
│   │   │   └── handlers.ts                # MSW API mock handlers
│   │   ├── LogsTable.test.tsx
│   │   ├── MachineHealthCard.test.tsx
│   │   └── FleetStatsBar.test.tsx
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── Dockerfile
│
├── infra/
│   ├── cdk/                               # AWS CDK app (TypeScript)
│   │   ├── bin/
│   │   │   └── app.ts                     # CDK entry point
│   │   ├── lib/
│   │   │   ├── vpc-stack.ts               # VPC, subnets, security groups
│   │   │   ├── ecr-stack.ts               # ECR repositories
│   │   │   ├── ecs-stack.ts               # ECS Fargate service + ALB
│   │   │   ├── frontend-stack.ts          # S3 bucket + CloudFront distribution
│   │   │   └── bedrock-stack.ts           # IAM role for Bedrock access
│   │   ├── cdk.json
│   │   └── package.json
│   ├── docker-compose.yml                 # Full local stack
│   ├── docker-compose.dev.yml             # Dev overrides (hot reload)
│   └── nginx/
│       └── nginx.conf
│
├── .github/
│   └── workflows/
│       ├── ci.yml                         # PR: lint + test (backend + frontend)
│       └── cd.yml                         # main merge: build → ECR → CDK deploy
│
├── assets/
│   ├── Coding-Assignment.docx
│   └── manufacturing_floor_logs_1000.csv
│
├── .env.example                           # Root-level example (docker compose uses this)
├── README.md                              # Public-facing project overview
├── PLANNING.md                            # This file
└── README_AI.md                           # AI usage log (required by assignment)
```

---

## 5. LangGraph Workflow Detail

### State Definition

```python
class AnalysisState(TypedDict):
    machine_summaries: list[dict]      # Input: per-machine aggregated stats
    llm_raw_response: str              # Raw LLM output string
    parsed_result: dict | None         # Parsed JSON (if schema passes)
    validation_errors: list[str]       # Collected validation failure messages
    retry_count: int                   # Current retry attempt (0-indexed)
    final_result: dict | None          # Output: stored to DB if successful
    error_state: str | None            # Set if all retries exhausted
```

### Graph Nodes

The `aggregate` step (DB query → summaries) happens in `app/services/summarizer.py` before the graph is invoked. The graph receives clean data and has no DB dependency.

| Node | Input | Output | Failure Mode |
|---|---|---|---|
| `call_llm` | `machine_summaries` + `validation_errors` | `llm_raw_response` | Network error → raise |
| `call_llm` | `machine_summaries` + `validation_errors` | `llm_raw_response` | Network error → raise |
| `validate` | `llm_raw_response` | `parsed_result` or `validation_errors` appended | Never raises — captures errors |
| `persist` | `parsed_result` | `final_result`, written to DB | DB error → propagate |
| `error_state` | exhausted retries | `error_state` message | — |

### Conditional Router

```python
def route_after_validate(state: AnalysisState) -> str:
    if state["parsed_result"] is not None:
        return "persist"
    elif state["retry_count"] < settings.MAX_AI_RETRIES:
        return "call_llm"       # Loop back with accumulated errors in prompt
    else:
        return "error_state"
```

### Prompt Strategy

**System prompt (constant):**
> You are an industrial equipment risk analyst. Given machine telemetry summaries, identify the top 3 at-risk machines. Return ONLY valid JSON matching the required schema. No preamble, no explanation outside the JSON.

**User prompt (dynamic, retry-aware):**
```python
def build_prompt(summaries: list[dict], errors: list[str] = []) -> str:
    base = f"Analyze these machine summaries:\n{json.dumps(summaries, indent=2)}"
    if errors:
        base += f"\n\nPrevious attempt failed validation. Fix these issues:\n"
        base += "\n".join(f"- {e}" for e in errors)
    return base
```

---

## 6. API Design

### Endpoints

```
POST  /api/logs/ingest              Upload CSV → parse → bulk insert
GET   /api/logs                     Paginated logs (filters: machine_id, status, from, to)
GET   /api/machines                 All machines with aggregated error/warning counts
GET   /api/machines/{machine_id}    Single machine detail + recent logs

POST  /api/analysis/run             Trigger LangGraph workflow (async, returns job_id)
GET   /api/analysis/status/{job_id} Poll job status (pending | running | complete | error)
GET   /api/analysis/latest          Most recent successful analysis result
GET   /api/analysis/history         Paginated list of all past analyses
```

### Key Response Schemas

**`GET /api/analysis/latest`**
```json
{
  "id": "uuid",
  "created_at": "2026-03-22T10:00:00Z",
  "top_at_risk_machines": [
    {
      "machine_id": "MCH-08",
      "risk_level": "high",
      "risk_score": 0.91,
      "reason": "4 errors and 20 warnings; temperature peaks at 102°F",
      "affected_sensors": ["temperature", "vibration"],
      "recommended_action": "Immediate inspection of thermal management system"
    }
  ],
  "fleet_summary": "8 machines analyzed. 3 flagged.",
  "retry_count": 0,
  "model_used": "gpt-4o-mini",
  "provider": "openai"
}
```

---

## 7. Frontend UI Design

**Design principle:** "Show a lot at a glance, hide the details until needed." Light theme. Information-dense but not cluttered.

### Dashboard (`/`)
```
┌─────────────────────────────────────────────────────────┐
│  IoT Maintenance Dashboard              [Ingest CSV]     │
├────────────┬────────────┬────────────┬──────────────────┤
│ 8 Machines │ 1,000 Logs │ 10 Errors  │ Last: 2min ago  │
├─────────────────────────────────────────────────────────┤
│ Filters: [All Machines ▼] [All Status ▼] [Mar 1–4]      │
├─────────────────────────────────────────────────────────┤
│ Timestamp      │ Machine │ Temp  │ Vibration │ Status   │
│ Mar 4, 18:22   │ MCH-08  │ 102°F │ 1.24      │ ● ERROR  │
│ Mar 4, 17:11   │ MCH-05  │ 94°F  │ 0.98      │ ▲ WARN   │
│ ...            │ ...     │ ...   │ ...       │ ● OK     │
└─────────────────────────────────────────────────────────┘
```

### Trends (`/trends`)
```
┌─────────────────────────────────────────────────────────┐
│  AI Maintenance Analysis              [Run Analysis]     │
│  Last run: Mar 22, 2026 at 10:00 AM                     │
├─────────────────────────────────────────────────────────┤
│  ┌──── MCH-08 ─────────────────────────────────────┐   │
│  │  ██ HIGH RISK   Score: 0.91                      │   │
│  │  Sensors: temperature  vibration                 │   │
│  │  "4 errors in 4 days, temp peaks at 102°F"       │   │
│  │  → Immediate inspection of thermal system        │   │
│  └──────────────────────────────────────────────────┘   │
│  (similar cards for MCH-05 and MCH-01)                  │
├─────────────────────────────────────────────────────────┤
│  MCH-08 Sensor Trends                                   │
│  [Temperature/Vibration dual-axis line chart]           │
│  [Error points highlighted in red]                      │
└─────────────────────────────────────────────────────────┘
```

**Risk badge colors:**
- `high` → red background (`bg-red-100 text-red-800 border-red-200`)
- `medium` → amber (`bg-amber-100 text-amber-800 border-amber-200`)
- `low` → green (`bg-green-100 text-green-800 border-green-200`)

---

## 8. AWS CDK Architecture

```
                    ┌─────────────────────────────────────────────────┐
                    │                   AWS Account                   │
                    │                                                 │
  Browser  ──────→  │  CloudFront ──→ S3 (React build)              │
                    │       │                                         │
                    │       └──→ ALB ──→ ECS Fargate (FastAPI)       │
                    │                        │                        │
                    │                   EFS Volume                   │
                    │                  (SQLite DB)                   │
                    │                        │                        │
                    │               Bedrock (Claude Haiku)           │
                    │                        │                        │
                    │            Secrets Manager                     │
                    │           (OPENAI_KEY or IAM role)             │
                    └─────────────────────────────────────────────────┘
```

### CDK Stacks

| Stack | Resources | Notes |
|---|---|---|
| `VpcStack` | VPC, 2 AZs, private + public subnets, NAT Gateway | Shared by all stacks |
| `EcrStack` | ECR repo for backend | Images tagged by commit SHA |
| `EcsStack` | ECS cluster, Fargate task, ALB, EFS mount, Secrets Manager ref | Backend runtime |
| `FrontendStack` | S3 bucket (private), CloudFront distribution, OAI | Static assets |
| `BedrockStack` | IAM role with `bedrock:InvokeModel` permission, attached to ECS task role | Prod AI access |

### GitHub Actions CD Flow

```yaml
# On push to main:
1. Build backend Docker image
2. Push to ECR (tagged with git SHA + latest)
3. Build frontend (npm run build)
4. Sync dist/ to S3
5. Invalidate CloudFront cache
6. cdk deploy --all --require-approval never
```

Secrets in GitHub Actions: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_ACCOUNT_ID`.

---

## 9. Environment Variables

```bash
# .env.example

# LLM Provider (local: openai, prod: bedrock)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Bedrock (prod only — uses IAM role in AWS, no key needed)
BEDROCK_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-haiku-4-5-20251001-v1:0

# Database
DATABASE_URL=sqlite+aiosqlite:///./iot_dashboard.db

# API
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO

# AI Workflow
MAX_AI_RETRIES=3
ANALYSIS_RATE_LIMIT_SECONDS=30
```

---

## 10. Testing Strategy

### Backend Coverage Targets (>80% overall)

| File | Test Type | Key Cases |
|---|---|---|
| `services/ingestion.py` | Unit | valid CSV, missing columns, duplicate rows, empty file |
| `services/summarizer.py` | Unit | correct aggregation math, handles machines with zero events |
| `services/validator.py` | Unit | valid pass, missing fields, wrong type, score/level contradiction, empty sensors + high risk, unknown machine_id, non-descending scores |
| `services/workflow.py` | Unit (mocked LLM) | happy path, 1 retry, 3 retries → error state, LLM network error |
| `api/routes/logs.py` | Integration | ingest 200, ingest bad CSV 422, GET with pagination, GET with filters |
| `api/routes/analysis.py` | Integration | trigger run, poll status, get latest, history pagination |

### Frontend Coverage Targets

| Component | Key Cases |
|---|---|
| `LogsTable` | Renders rows, pagination controls, status badge colors, empty state |
| `MachineHealthCard` | All risk levels render correct colors, missing `recommended_action` graceful |
| `FleetStatsBar` | Correct counts from mock data, zero-state |
| `AnalysisTrigger` | Loading state during run, error toast on failure |

---

## 11. Step-by-Step Build Order

### Phase 1 — Backend Foundation
```
1.1  [ ] Init backend/ directory, pyproject.toml / requirements files
1.2  [ ] core/config.py (pydantic-settings, all env vars)
1.3  [ ] core/database.py (async SQLAlchemy engine, session dep)
1.4  [ ] ORM models: LogEntry, Machine, AnalysisResult
1.6  [ ] services/ingestion.py (CSV parse + bulk upsert)
1.7  [ ] POST /logs/ingest endpoint
1.8  [ ] GET /logs (paginated, filtered) + GET /machines
1.9  [ ] main.py (app factory, CORS, lifespan startup)
1.10 [ ] tests/conftest.py (in-memory SQLite fixture, test client)
1.11 [ ] test_ingestion.py + test_routes.py (Phase 1 coverage)
```

### Phase 2 — AI Workflow
```
-- app layer (talks to DB) --
2.1  [ ] app/services/summarizer.py (DB → per-machine stats dict)
2.2  [ ] app/schemas/analysis.py (strict Pydantic schema for LLM output)

-- agent layer (no DB, no HTTP) --
2.3  [ ] agent/prompts.py (system + user prompt builders, retry-aware)
2.4  [ ] agent/llm.py (LangChain LLM factory, OpenAI + Bedrock via config)
2.5  [ ] agent/validator.py (Stage 1: Pydantic schema, Stage 2: logic checks)
2.6  [ ] agent/workflow.py (LangGraph graph: summarize → LLM → validate → retry)

-- back to app layer --
2.7  [ ] POST /analysis/run (calls summarizer → hands off to agent/workflow)
2.8  [ ] GET /analysis/status/{job_id} + GET /analysis/latest + GET /analysis/history

-- tests --
2.9  [ ] test_summarizer.py (unit: aggregate stats)
2.10 [ ] test_validator.py (unit: all 20+ validation paths, pure Python)
2.11 [ ] test_workflow.py (unit: LangGraph with mocked LLM)
2.12 [ ] test_routes.py (integration: analysis endpoints)
```

### Phase 3 — Frontend
```
3.1  [ ] Init frontend/ with Vite + React + TypeScript
3.2  [ ] Install + configure Tailwind + shadcn/ui
3.3  [ ] types/index.ts (TypeScript types matching API schemas)
3.4  [ ] api/client.ts (typed fetch wrappers)
3.5  [ ] hooks/useLogs.ts + hooks/useMachines.ts (React Query)
3.6  [ ] hooks/useAnalysis.ts (trigger + poll)
3.7  [ ] layout/Navbar.tsx + layout/PageShell.tsx
3.8  [ ] FleetStatsBar.tsx
3.9  [ ] RiskBadge.tsx
3.10 [ ] LogsTable.tsx (with pagination + filters)
3.11 [ ] Dashboard.tsx page (/ route)
3.12 [ ] MachineHealthCard.tsx
3.13 [ ] SensorChart.tsx (Recharts dual-axis)
3.14 [ ] AnalysisTrigger.tsx
3.15 [ ] Trends.tsx page (/trends route)
3.16 [ ] App.tsx (React Router setup)
3.17 [ ] MSW mock handlers + frontend tests
3.18 [ ] Error boundaries + toast notifications (Sonner)
3.19 [ ] Loading skeletons on all data-fetching components
```

### Phase 4 — Containers
```
4.1  [ ] backend/Dockerfile (multi-stage: build + slim runtime)
4.2  [ ] frontend/Dockerfile (multi-stage: node build + nginx serve)
4.3  [ ] infra/nginx/nginx.conf (proxy /api/* to backend, /* to frontend)
4.4  [ ] infra/docker-compose.yml (nginx + backend + frontend)
4.5  [ ] infra/docker-compose.dev.yml (hot reload overrides)
4.6  [ ] .env.example (root level)
4.7  [ ] Smoke test: docker compose up → ingest CSV → run analysis → see results
```

### Phase 5 — CI/CD
```
5.1  [ ] .github/workflows/ci.yml (ruff + mypy + pytest + vitest on every PR)
5.2  [ ] .github/workflows/cd.yml (build → ECR → S3 → CDK deploy on main)
5.3  [ ] Branch protection rules (require CI pass before merge)
```

### Phase 6 — AWS CDK
```
6.1  [ ] infra/cdk/ project init (cdk init app --language typescript)
6.2  [ ] VpcStack
6.3  [ ] EcrStack
6.4  [ ] EcsStack (with EFS for SQLite persistence + Secrets Manager)
6.5  [ ] FrontendStack (S3 + CloudFront)
6.6  [ ] BedrockStack (IAM role for Fargate task)
6.7  [ ] Wire CDK stacks together in bin/app.ts
6.8  [ ] cdk bootstrap (one-time per account/region)
6.9  [ ] Manual first deploy: cdk deploy --all
6.10 [ ] Update cd.yml to use CDK
```

### Phase 7 — Polish
```
7.1  [ ] Dark mode support (Tailwind dark: classes + OS preference)
7.2  [ ] Accessibility audit (ARIA labels, keyboard nav, color contrast)
7.3  [ ] Rate limiting on POST /analysis/run (in-memory, 30s cooldown)
7.4  [ ] Structured logging (structlog → JSON in prod, pretty in dev)
7.5  [ ] README_AI.md (prompts used, AI errors, manual fixes)
7.6  [ ] Final README.md review
```

---

## 12. Success Criteria

### Functional
- [ ] `docker compose up` → full stack running, zero manual steps
- [ ] CSV ingest → 1,000 rows in dashboard table with correct filters
- [ ] "Run Analysis" → within 10s → 3 health cards with structured AI output
- [ ] Validator rejects malformed/contradictory responses and retries automatically
- [ ] Analysis history shows all past runs with timestamps

### Quality
- [ ] Backend test coverage ≥ 80%
- [ ] Frontend tests pass with MSW mocks
- [ ] CI pipeline green on every PR
- [ ] `ruff check` and `mypy` pass with zero errors
- [ ] TypeScript `tsc --noEmit` passes

### Infrastructure
- [ ] `cdk deploy` provisions all AWS resources from scratch
- [ ] GitHub Actions deploys on merge to main automatically
- [ ] OpenAPI docs at `/api/docs`
- [ ] Frontend accessible via CloudFront URL

---

## 13. Known Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Bedrock model access not approved in AWS account | Medium | Request access early; fallback to OpenAI with env var switch |
| SQLite concurrency issues on EFS in multi-task ECS | Low (single task) | Single Fargate task for now; migration path to RDS is one config change |
| LLM returns valid schema but wrong machine IDs | Low (validated) | Stage 2 validator cross-checks against DB |
| CDK bootstrap not done for target account | Low | Document in README; one-time setup |
| Rate limits on OpenAI during CI tests | Medium | All AI calls mocked in tests; no real LLM calls in CI |
