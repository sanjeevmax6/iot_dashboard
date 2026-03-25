# README_AI — How I Built This with AI Assistance

> This document covers how I used AI tools during development: which prompts generated code, how I verified the AI's output, and what I had to fix or write manually.

---

## Table of Contents

1. [AI Tools Used](#ai-tools-used)
2. [Prompts That Generated Code](#prompts-that-generated-code)
3. [How I Verified the AI's Logic](#how-i-verified-the-ais-logic)
4. [What I Fixed Manually](#what-i-fixed-manually)
5. [What I Wrote Without AI](#what-i-wrote-without-ai)
6. [Reflections](#reflections)

---

## AI Tools Used

| Tool | Used For |
|---|---|
| Claude Sonnet (via Claude Code CLI) | Architecture planning, CDK infrastructure, CI/CD, debugging |

---

## Prompts That Generated Code

Rather than showing the raw back-and-forth, each section below shows the **intent** behind the prompting sequence — what I was actually trying to achieve and how I directed the AI toward it.

---

### 1. Project Scaffolding

#### Step 1 — Configure Claude Code before writing a line of code

Before prompting for any implementation, I set up the Claude Code environment in `.claude/`:

- **`settings.json`** — added two hooks: a `UserPromptSubmit` hook that logs every prompt I send (via `claude_logger.py`) and a `Stop` hook that logs when each response completes. This gave me a full audit trail of every AI interaction throughout the project, which is what feeds this document.
- **`claude_logger.py`** — a lightweight script that appends timestamped prompt entries to `.claude/claude_logs/`, one log file per day.

The goal was to have an automated record from the start, so I wouldn't have to reconstruct what I asked the AI after the fact.

#### Step 2 — Generate a PLANNING.md as the source of truth

Rather than jumping straight into code, I asked the AI to reason through the full architecture first and produce a living planning document:

**Prompt:**
```
I want to build a production-grade IoT dashboard — not just what the
assignment asks for. Walk me through the best architecture, then document
it comprehensively in a PLANNING.md before writing any code. Cover key
decisions and trade-offs, full tech stack with justifications, repo
structure, API design, UI layout, CDK architecture, test strategy, and
a phased build order with checkboxes. Don't over-engineer — stay close
to the requirements but build something genuinely production-quality.
```

This produced `.claude/thoughts/PLANNING.md` — a 700-line document covering:

#### Step 3 — Use PLANNING.md iteratively as a contract

Every subsequent prompt referenced the plan. When building each phase, I'd point the AI back to the relevant PLANNING.md section, and after completing a phase I'd update the checklist. This kept the AI's context anchored and prevented drift.

#### Tech stack specified in the plan iteratively once the architeture was ready but when there was no clear direction

**Backend:** FastAPI 0.115, uvicorn, SQLAlchemy 2.0 async, aiosqlite, pydantic-settings, langchain-core, langchain-openai, langchain-aws, langgraph, langchain-community (ConversationBufferMemory), structlog, ruff, mypy, pytest + pytest-asyncio + pytest-cov, httpx

**Frontend:** React 18, TypeScript 5, Vite 5, TanStack Query v5, React Router v6, Tailwind CSS, shadcn/ui (Radix), Recharts, Lucide React, date-fns, Sonner — tested with Vitest, Testing Library, MSW

**Infrastructure:** Docker + Docker Compose, Nginx (reverse proxy + SPA static server), AWS CDK (TypeScript) — VPC, ECR, ECS Fargate, ALB, S3, CloudFront, Secrets Manager, GitHub Actions (CI + CD + deploy + destroy workflows)

**Notes:**
The AI produced solid boilerplate for the FastAPI lifespan handler, CORS config, and async engine setup. 
I did a lot of modifications, for example, inducing foreign keys between tables machines and log_entry tables.
I identified this as a latency problem at scale and added them manually.

---

### 2. CSV Ingestion Endpoint

**Prompt:**
```
Build a CSV ingestion endpoint that accepts a file upload, bulk-inserts records
into the async SQLAlchemy session, and returns a summary of inserted vs skipped
rows. Also I will potentially be adding a "Clear Data" button on the frontend that wipes the database
before re-ingesting. So make sure to consider CRUD operations as the standard and design for future api routes as well.
```

**Notes:**
The ingestion logic and deduplication worked well out of the box. The streaming progress feedback required additional back-and-forth to get the SSE (Server Sent Events) framing right.
This is something I wanted to allow an AI embedded design.

---

### 4. Validation Layer

**Prompt:**
```
The LLM must return a structured JSON response matching this Pydantic schema of the langgraph workflow already built.
Enforce these consistency rules in the validator:
  - risk_score is a float 0.0–1.0
  - high: risk_score >= 0.7, medium: 0.3 <= risk_score < 0.7, low: < 0.3
  - machines must be returned sorted by risk_score descending
  - machine_ids must exist in the ingested dataset

If any rule fails, return a structured error string that the LLM can use as
a self-correction instruction on the next retry — not just a boolean.
```

**Notes:**
The schema and Pydantic validation worked first try. The subtler issue was the retry prompt. The LLM kept producing scores like 0.65 for "high" (intuitively reasonable, but out of bounds). The original correction message wasn't emphatic enough about the boundaries. I rewrote the retry prompt to restate the exact thresholds.

---

### 5. Intent Classifier + Session Memory

**Prompt:**
```
Transform the analysis page into a conversational interface. The analyze
button should live inside the chat input. Add a persistent chat window for
follow-up questions about machine risk health, backed by LangChain (not LangGraph) buffer memory
so conversation history is maintained per session_id.

Also add an intent guard that classifies each message as ON_TOPIC or OFF_TOPIC before it reaches the
main LLM. This is to majorily save tokens and first final layer of prompt injections. 
Refuse off-topic questions with a canned response to prevent
token waste. Also I'd like to stream the thoughts/process as a collapsible "thinking" panel for the LLM's reasoning
steps, similar to how Cursor surfaces agent thoughts. 
```

**Files generated:**
- `backend/agent/chat.py`
- `backend/app/api/routes/chat.py`

**Notes:**
Two issues required manual fixes: 
(1) when analysis was triggered via the chat route, the result was never persisted to the DB — `useLatestAnalysis()` on the frontend never updated. I separated the analysis and chat routes so analysis always writes to the DB regardless of context. 
(2) Bedrock streaming uses `InvokeModelWithResponseStream` (a different IAM action from `InvokeModel`). The AI didn't know this and the error was caught silently. I found it by reading the raw SSE event stream and added the correct IAM permission to the ECS task role.

---

### 7. React Frontend & Dashboard

**Prompt:**
```
Build a React + TypeScript dashboard. Layout: chatbox centered when no
results exist; transitions to a multi-column layout (chat left, top-3
machines right, trends chart bottom) once analysis runs. Use Recharts for
sensor time-series. Try to have base themes in app.css and other component specific styles inline with tailwind CSS. 
Use React Query (only if required) for server state and custom hooks for shared logic.
```

**Files generated / shaped:**
- `frontend/src/App.tsx`
- `frontend/src/pages/`
- `frontend/src/components/`
- `frontend/src/hooks/`
- `frontend/src/css/`

**Notes:**
The AI defaulted to mixing styles inline and inside component files. I redirected it to a clean `css/` folder structure for maintainability. The responsive layout transition (centered → multi-column on results) needed a few iterations to get the flexbox logic right.

---

### 9. AWS CDK Infrastructure

**Prompt:**
```
Write AWS CDK TypeScript stacks: VPC with NAT Gateway, ECR repo, ECS Fargate
service behind an ALB, S3 + CloudFront for the frontend.
Add removal policies to all stateful resources (VPC, ALB, ECS cluster) so cdk destroy
leaves no orphaned resources billing the account.
```

**Notes:**
The AI-generated CDK had no resource cleanup story. no removal policies on VPC, ALB, and ECS cluster. It managed to do this for other resources. 
I carefully checked my AWS Console and the CLI to see any estranged ones and fixed this.

---

## How I Verified the AI's Logic

1) I iteratively wrote tests along with the features I built, both for backend and frontend and set the CI pipeline to not pass if coverage is less than 80%.
2) Asserted each case returned the correct structured error string in Langgraph workflow. Since the error message is what gets fed back to the LLM as a correction instruction, I keenly monitored that.
3) Used the FastAPI `/docs` Swagger UI to test every endpoint with some edge-case I could think of before automating tests. Specifically I tested the end points, chat, analyze and ingest as they were the functional ones.
4)  Used the browser network tab to watch the raw SSE event stream during chat. This is how I caught the silent streaming failure. The backend seemed to only return `{"type": "error", ...}` events that the frontend was silently ignoring. Since I wanted this specific behavior and I've designed it the wrong way before, I monitored it closely.

---

## What I Fixed Manually

| # | File(s) | What the AI Got Wrong | What I Changed |
|---|---|---|---|
| 1 | `backend/app/models/` | Tables had no foreign keys — functional but would cause full table scans at scale | Added FK relationships between log entries and machine records |
| 2 | `backend/agent/graph.py` | Routing on retry/failure used ambiguous conditional logic — graph could loop indefinitely | Replaced with explicit Lambda-style conditional edges so every node exit is deterministic |
| 3 | `backend/agent/chat.py` | Basic chat endpoint was stateless — no memory between messages in the same session | Added per-session LangChain buffer memory and conversation history |
| 4 | `backend/agent/validator.py` + `backend/agent/prompts.py` | Retry prompt wasn't emphatic enough — LLM kept producing 0.65 for "high" (intuitive but out of bounds) | Rewrote the correction instruction to restate exact thresholds inline, making it hard to misread under structured output constraints |
| 5 | `backend/agent/graph.py` + `frontend/src/hooks/` | Analysis triggered via chat was never persisted to DB — `useLatestAnalysis()` never updated, sidebar stayed empty | Separated analysis and chat routes; analysis always writes to DB regardless of entry point |
| 6 | `backend/app/api/routes/` | Chat and analysis logic merged into one route — no way to enforce different machine-count logic per context | Split into dedicated routes with separate count validation |
| 7 | `backend/agent/chat.py` | No intent validation — every message hit the main LLM, wasting tokens on off-topic queries | Added lightweight intent guard (ON_TOPIC / OFF_TOPIC classifier) before the main LLM call |
| 8 | `infra/nginx/nginx.conf` + `frontend/nginx.conf` | Single nginx config conflated reverse proxy and static file serving roles | Split into two: `infra/nginx/nginx.conf` (reverse proxy, port 80) and `frontend/nginx.conf` (SPA static server with `try_files`) |
| 9 | `infra/cdk/lib/ecr-stack.ts` | `cdk destroy` left ECR images behind — fails silently on a non-empty repo | Added `emptyOnDelete: true` so destroy is fully clean |
| 10 | `backend/Dockerfile` + `.github/workflows/` | No `--platform linux/amd64` flag — Apple Silicon builds arm64 images, Fargate expects amd64 | Added `--platform linux/amd64` to all Docker build commands |
| 11 | `backend/agent/llm_rerouter.py` | AI defaulted to Claude Haiku on Bedrock, which requires manual model access approval per AWS account | Switched to Amazon Nova Lite — no manual enablement needed, works in a fresh account |
| 12 | `infra/cdk/lib/ecs-stack.ts` | Task role only had `bedrock:InvokeModel` — streaming chat uses a different API action (`InvokeModelWithResponseStream`) | Added `InvokeModelWithResponseStream` to the task role policy |
| 13 | `infra/cdk/lib/vpc-stack.ts` + `ecs-stack.ts` | No removal policies — VPC (NAT ~$32/month) and ALB (~$16/month) would be orphaned after destroy | Added `removalPolicy: DESTROY` / `applyRemovalPolicy(DESTROY)` on all stateful constructs |
| 14 | `.github/workflows/deploy.yml` + `destroy.yml` | No concurrency guard — parallel `workflow_dispatch` runs would race on CloudFormation | Added `concurrency:` block to both workflows |
| 15 | `.github/workflows/ci.yml` | CI triggered twice on the same commit (push + PR open) | Added conditional to run only once per commit |

---

## Reflections

### What worked well
AI was fast at boilerplate. Dockerfiles, Pydantic schemas, GitHub Actions skeleton. I could describe the shape of what I wanted and get to 80% in one prompt. In my opinon, the LLM provider factory (`llm_rerouter.py`) and the Pydantic schema definitions both worked cleanly on the first attempt. The AI was also good as a thinking partner for architecture trade-offs, for example, Github Secrets vs AWS Secrets Manager.

### Where AI fell short
Anything involving two interacting systems at once. The AI got each component right. These bugs were only visible at integration time, not during code generation. Personally, since there was no sandbox for cloud deployments, the tool did produce a bug-versioned skeleton. I had to look at resources that I powered, and then gracefully shut them down. Moreover, certain retention policies too were out of contexts. Since I wanted a clean graceful shutdown, I had to handle those conditions too.

### What I'd do differently
- Write CI and tests alongside the implementation, not after. Frontend tests were retrofitted at the end, which took longer than building them in parallel would have.
- Decouple the database from the backend container earlier. Right now whenver I rebuild the image, the DB gets wiped down, as right now the database is attached directly to the container. Since the use case was ingesting csv manually, and not in real time, I avoied overcomplicating things.
- Enhance the context of LLMs by attaching tools that can give access to a part of the data so that the LLM can be more robust when deployed as the go to tool for the manufacturing floor.
- Optimizing batch upload process to a parallelized ingestion to DB to enable seamless behavior. Maybe I could have pivoted this to a background task as well, but maybe an overshot for v1 of this project.
- Increase the speed of LLMs by creating a different mechanism for gating