# AKS AI Observability

Learning / portfolio project: run a small **LLM proxy API** on **Azure Kubernetes Service (AKS)**, with production-style **metrics, logs, and alerts** — plus a lightweight **eval gate in CI** (SDET angle).

Companion learning path: [docs/project-roadmap.md](docs/project-roadmap.md).

## Why this project

| Goal | How this helps |
|------|----------------|
| Career depth (2026) | Operate AI on cloud + Kubernetes (MLOps / platform adjacent) |
| Azure | AKS, Azure OpenAI, Monitor / Managed Prometheus |
| SDET crossover | pytest + golden-prompt evals that can fail CI |
| Reuse | FastAPI, GitHub Actions, Terraform habits you already know |

## Stack (target)

- **Python 3.13** + **FastAPI** — thin `/v1/chat` proxy in front of Azure OpenAI
- **Docker** → **AKS**
- **Terraform** — resource group, AKS, related Azure bits
- **OpenTelemetry** and/or **Azure Monitor** — latency, errors, tokens, cost
- **GitHub Actions** — test → build image → deploy (gated)
- **Small eval suite** — golden prompts; optional LLM-as-judge later

## What you monitor (summary)

- API: rate, errors, p95 latency  
- Model: tokens, estimated cost, 429s / content filters  
- Cluster: pod health, CPU/memory, restarts  

Full list and phases: [docs/project-roadmap.md](docs/project-roadmap.md).

## Status

Phases are **not started**. Use the roadmap checklist as you build.
