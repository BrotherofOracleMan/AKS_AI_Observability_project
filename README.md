# AI on Kubernetes

Learning / portfolio project: **Dockerize** a FastAPI **Azure OpenAI proxy**, run it on **Kubernetes** (Kind first), then deploy the same manifests to **AKS** with **Terraform**.

Companion learning path: [docs/project-roadmap.md](docs/project-roadmap.md).

## What this project is

A small FastAPI **LLM proxy** (`/v1/chat`) that sits between clients and **Azure OpenAI**. Clients call *your* API; you forward the prompt to a hosted model and return the reply.

**The point:** prove you can run **AI inference as a real workload on Kubernetes** — container, manifests, cluster, CI — not as a one-off script or Jupyter notebook experiment.

**Core path:** stub API → Azure OpenAI → Docker → Kind → Terraform/AKS → thin CI  

**Advanced (later):** Workload Identity → thin RAG → thin evals → GitOps  

**Out of scope:** heavy observability (covered at work), GPU pools, service mesh, multi-cluster, fine-tuning.

## Why this project

| Goal | How this helps |
|------|----------------|
| Docker | Ship a real API image, not only `uvicorn` on a laptop |
| Kubernetes | Deployments, Services, probes, Secrets — Kind then AKS |
| AI | Thin `/v1/chat` proxy in front of **Azure OpenAI** |
| IaC | **Terraform** for AKS create/destroy |
| Advanced | Workload Identity, thin RAG, thin evals, GitOps |

## Stack (target)

- **Python 3.13** + **FastAPI** — `/health` + `/v1/chat` proxy
- **Docker** → **Kind** → **AKS** (same manifests)
- **Terraform** — RG + AKS in `infra/`
- **Azure OpenAI** — hosted chat model
- **GitHub Actions** — pytest (mocked OpenAI) → build image (optional deploy)

**Advanced (after core):** Workload Identity → thin RAG → thin evals → GitOps.

## Local setup (Phase 0)

```bash
uv sync --group dev
cd src && uv run uvicorn main:app --reload
```

- Health: http://localhost:8000/health  
- Docs: http://localhost:8000/docs  
- Chat: `POST /v1/chat` with `{"messages":[{"role":"user","content":"hello"}]}`

```bash
uv run pytest -v
```

Everything lives in `src/main.py` for now (stub echo, no Azure). Split files when Phase 1 needs them.

## Path (summary)

Same as [What this project is](#what-this-project-is). Details and checklists: [docs/project-roadmap.md](docs/project-roadmap.md).

## Status

Phase 0 skeleton is in place. Next: Phase 1 (Azure OpenAI).
