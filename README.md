# AI on Kubernetes

Learning / portfolio project: **Dockerize** a FastAPI **Azure OpenAI proxy**, run it on **Kubernetes** (Kind first), then deploy the same manifests to **AKS** with **Terraform**.

Companion learning path: [docs/project-roadmap.md](docs/project-roadmap.md).

## What this project is

A small FastAPI **LLM proxy** (`/v1/chat`) that sits between clients and **Azure OpenAI**. Clients call *your* API; you forward the prompt to a hosted model and return the reply.

**The point:** prove you can run **AI inference as a real workload on Kubernetes** — container, manifests, cluster, CI — not as a one-off script or Jupyter notebook experiment.

**Core path:** stub API → Azure OpenAI → Docker → Kind → thin CI → evals → AKS (Terraform)

**Advanced (later):** Workload Identity → thin RAG → GitOps — see [docs/deferred-phases.md](docs/deferred-phases.md)

**Out of scope:** heavy observability (covered at work), GPU pools, service mesh, multi-cluster, fine-tuning.

## Why this project

| Goal | How this helps |
|------|----------------|
| Docker | Ship a real API image, not only `uvicorn` on a laptop |
| Kubernetes | Deployments, Services, probes, Secrets — Kind then AKS |
| AI | Thin `/v1/chat` proxy in front of **Azure OpenAI** |
| CI / quality | Mocked pytest, smoke, eval gates |
| IaC | **Terraform** for AKS create/destroy (Phase 6) |

## Stack

- **Python 3.13** + **FastAPI** — `/health` + `/v1/chat` proxy
- **Docker** → **Kind** → **CI** → **evals** → **AKS** (same manifests)
- **GitHub Actions** — mocked pytest → build image
- **Terraform** — RG + AKS in `infra/` (Phase 6)
- **Azure OpenAI** — hosted chat model

**Advanced (after Phase 6):** Workload Identity, thin RAG, GitOps — [docs/deferred-phases.md](docs/deferred-phases.md).

## Local setup

```bash
uv sync --group dev
cp .env.example .env   # fill in Azure OpenAI values
uv run python -m uvicorn main:app --reload --app-dir src
```

- Health: http://localhost:8000/health  
- Docs: http://localhost:8000/docs  
- Chat: `POST /v1/chat`

```bash
curl -s http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{"messages":[{"role":"user","content":"hello"}]}'
```

Response shape (approx):

```json
{
  "provider_message_id": "chatcmpl-...",
  "completion": {
    "text": "...",
    "model": "gpt-4.1-mini",
    "prompt_tokens": 19,
    "completion_tokens": 50,
    "total_tokens": 69
  }
}
```

```bash
uv run pytest -m "not live" -v
```

`-m "not live"` runs only the mocked tests (they patch `main.chat`), so nothing calls Azure or spends tokens — same as CI. Plain `pytest` also runs the `live` tests, which need a running app at `BASE_URL`.

**Evals:** `tests/test_evals.py` — `pass_scorer` + mocked golden cases in CI (`-m "not live"`). Live grading: `pytest tests/test_evals.py -m live` (needs port-forward / `BASE_URL`). Smoke: `tests/test_smoke.py` / `./probe_smoke.sh`.

Layout: `src/main.py`, `config.py`, `openai_client.py`, `models.py`. Never commit `.env`.

## Status

Phases **0–6 done** — the same image ran on Kind and on AKS (Terraform + ACR + Kustomize overlay), with smoke + live evals passing on both. AKS is destroyed when idle.

| Doc | What's in it |
|-----|--------------|
| [docs/architecture.md](docs/architecture.md) | How it fits together, why a proxy, Kind vs AKS, K8s networking + secrets, how to explain it |
| [docs/runbook.md](docs/runbook.md) | AKS create → deploy → test → destroy, kubectl reference, debugging |
| [docs/project-roadmap.md](docs/project-roadmap.md) | Phase checklists |
| [docs/deferred-phases.md](docs/deferred-phases.md) | Optional next steps (API auth, Workload Identity, RAG, GitOps) |
