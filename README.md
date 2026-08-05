# AI on Kubernetes

Learning / portfolio project: **Dockerize** a FastAPI **Azure OpenAI proxy**, run it on **Kubernetes** (Kind first), then deploy the same manifests to **AKS** with **Terraform**.

Companion learning path: [docs/project-roadmap.md](docs/project-roadmap.md).

## Why this project

| Goal | How this helps |
|------|----------------|
| Docker | Ship a real API image, not only `uvicorn` on a laptop |
| Kubernetes | Deployments, Services, probes, Secrets — Kind then AKS |
| AI | Thin `/v1/chat` proxy in front of **Azure OpenAI** |
| IaC | **Terraform** for AKS create/destroy |

## Stack (target)

- **Python 3.13** + **FastAPI** — `/health` + `/v1/chat` proxy
- **Docker** → **Kind** → **AKS** (same manifests)
- **Terraform** — RG + AKS in `infra/`
- **Azure OpenAI** — hosted chat model
- **GitHub Actions** — pytest (mocked OpenAI) → build image (optional deploy)

**Advanced (after core):** Workload Identity, thin RAG, thin evals, GitOps.

**Out of scope:** heavy observability (covered at work), GPU pools, service mesh, multi-cluster, fine-tuning.

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

**Core:** stub → Azure OpenAI → Docker → Kind → Terraform/AKS → thin CI  

**Advanced:** Workload Identity → thin RAG → thin evals → GitOps  

Full checklist and readings: [docs/project-roadmap.md](docs/project-roadmap.md).

## Status

Phase 0 skeleton is in place. Next: Phase 1 (Azure OpenAI).
