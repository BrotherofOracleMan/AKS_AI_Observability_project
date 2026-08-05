# Project Roadmap: AI on Kubernetes

Learning-focused guide: containerize a FastAPI **Azure OpenAI proxy**, run it on **Kubernetes** (Kind first), then deploy the **same manifests** to **AKS**.

Repo folder may still be named `aks-ai-observability`; the hero skills are **Docker + Kubernetes + AI**. Heavy observability is out of scope here (covered at work).

---

## North star

```text
Client  -->  FastAPI (container on K8s)  -->  Azure OpenAI
                    ↑
         Docker image + K8s manifests
         (Kind first, then AKS)
```

**Interview one-liner:** “I containerized an LLM proxy, ran it on Kubernetes locally, then on AKS in front of Azure OpenAI — with keyless identity, and thin RAG/evals/GitOps on top.”

---

## Goals / non-goals

### Goals (core — Phases 0–5)

- Ship a real **API proxy** in front of Azure OpenAI (not a notebook)
- **Dockerize** the app and run it with env-injected config
- Learn **Kubernetes primitives** on Kind (Deployment, Service, probes, Secret)
- Provision **AKS with Terraform** and deploy the **same** manifests; destroy when idle
- Keep **thin** ops only: structured logs + basic token/request logging; `kubectl` for pod health
- Thin CI: pytest (mocked OpenAI) → build image (optional AKS deploy)

### Goals (advanced — after core)

- **Workload Identity** — pod → Azure OpenAI without long-lived keys in Secrets
- **Thin RAG** — tiny doc set, retrieve-then-generate behind the same proxy
- **Thin evals** — golden prompts that can fail CI (quality gate, not dashboards)
- **GitOps** — cluster desired state from git (Argo CD or Flux)

### Non-goals

- Heavy Azure Monitor / Prometheus / SLO dashboard portfolio work (doing similar at work)
- GPU node pools, service mesh, multi-cluster
- Fine-tuning / training jobs
- Go companion, deep ML theory, production multi-region platforms

---

## Target architecture

```
┌─────────────────┐     ┌──────────────────────────┐     ┌─────────────────┐
│  Client / CI    │────▶│  FastAPI (Deployment)    │────▶│  Azure OpenAI   │
│  curl, pytest   │     │  /health  /v1/chat       │     │  (+ optional    │
└─────────────────┘     │  logs + basic usage      │     │   RAG context)  │
                        └──────────────────────────┘     └─────────────────┘

Path:  code → Docker image → Kind (learn) → Terraform AKS (demo)
CI:    pytest (mocked OpenAI) → build/push image → optional deploy / GitOps

Advanced (later): Workload Identity | thin RAG | thin evals | GitOps
```

### Suggested repo layout (create as you go)

```
aks-ai-observability/
  README.md
  docs/
    project-roadmap.md      # this file
    architecture.md         # fill in after Kind/AKS
    runbook.md              # create/destroy AKS + how to debug pods
  src/
    main.py                 # start here (health + stub chat); split later
  tests/
    test_app.py
    evals/                  # optional Phase 8
  deploy/
    k8s/                    # Deployment, Service, probes, Secret examples
  infra/                    # Terraform (AKS, RG, …)
  .github/workflows/
  Dockerfile
  pyproject.toml
```

Later: `config.py`, `openai_client.py` when Phase 1 needs them.
---
## Thin ops (not the centerpiece)

Enough to debug and talk about cost — not a full observability product.

| Signal | How you see it (v1) |
|--------|---------------------|
| Request / error / latency | Structured logs from the proxy |
| Tokens per call | Log `usage` from Azure OpenAI responses |
| Pod health / restarts | `kubectl get pods`, describe, logs |
| 429 / provider errors | Log status; keep OpenAI quotas low |

---

## Phased plan

Mark items `[x]` as you finish. Stay on one phase until the “done when” bar is met.

**Readings:** **Known** = already familiar (refresher); **New** = focus study time.

### Phase 0 — Repo + local API skeleton

**Learn:** project layout, health endpoint, stub chat.

- [x] Create git repo; Python 3.13 + uv/pip; FastAPI app
- [x] `GET /health` → `{"status":"ok"}`
- [x] `POST /v1/chat` stub (echo or fake response) with Pydantic schemas
- [x] `.env.example` (no secrets in git)
- [x] Basic pytest for health + schema validation
- [x] README: how to run locally

**Done when:** `uvicorn` locally + pytest green with no Azure yet.

| Reading | Why | Status |
|---------|-----|--------|
| [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/) | App layout, Pydantic | Known |
| [Twelve-Factor — Config](https://12factor.net/config/) | Same env pattern → Docker → K8s | Known |
| [httpx / TestClient testing](https://fastapi.tiangolo.com/tutorial/testing/) | pytest for the proxy | Known |
| [LLM / AI gateway pattern](https://learn.microsoft.com/azure/api-management/azure-openai-api-from-specification) | Why a thin FastAPI front door | New |

---

### Phase 1 — Azure OpenAI integration

**Learn:** Azure OpenAI deployments, keys, token usage in responses.

- [ ] Create Azure OpenAI resource + chat deployment (cheapest suitable model)
- [ ] Wire real client (split `openai_client.py` / `config.py` when it helps)
- [ ] Return model text + record `usage` tokens on each call
- [ ] Structured logging: request id, latency_ms, tokens, status
- [ ] Unit tests with **mocked** OpenAI (no spend in CI)

**Done when:** local curl to `/v1/chat` hits Azure OpenAI; tests mock the provider.

**Cost note:** set low quotas; never commit keys; destroy lab resources when idle.

| Reading | Why | Status |
|---------|-----|--------|
| [Azure OpenAI concepts](https://learn.microsoft.com/azure/ai-services/openai/concepts/models) | Deployments vs models; tokens → cost | New |
| [Azure OpenAI quickstart (Python)](https://learn.microsoft.com/azure/ai-services/openai/chatgpt-quickstart) | First real chat call | New |
| [Completions / SDK usage](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/completions) | Tokens in responses | New |
| [Quotas & limits](https://learn.microsoft.com/azure/ai-services/openai/quotas-limits) | 429s, lab quotas | New |
| [Azure OpenAI pricing](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/) | Token/$ intuition | New |

---

### Phase 2 — Docker

**Learn:** ship the API as an image; config via env (12-factor).

- [ ] `Dockerfile` runs uvicorn (slim image; non-root if practical)
- [ ] `docker run` with env vars for OpenAI endpoint/key/deployment
- [ ] Optional: push to **Azure Container Registry (ACR)**

**Done when:** `docker run` serves `/health` and chat with env-injected secrets.

| Reading | Why | Status |
|---------|-----|--------|
| [What is a container?](https://learn.microsoft.com/dotnet/architecture/microservices/container-docker-introduction/) | Containers vs VMs | Known |
| [Docker best practices](https://docs.docker.com/build/building/best-practices/) | Slim image, layers, non-root | Known basics; **New** for shipping the API |
| [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) | `FROM`, `COPY`, `CMD` | New |

---

### Phase 3 — Kubernetes locally (Kind)

**Learn:** Deployment, Service, probes, Secret — before paying for AKS. This is the **main** K8s learning phase.

- [ ] Kind cluster
- [ ] Manifests under `deploy/k8s/`: Deployment + Service + liveness/readiness on `/health`
- [ ] Secret (or documented stub mode) for OpenAI endpoint/key/deployment
- [ ] Load image into Kind; `kubectl port-forward` smoke test
- [ ] Be able to explain probes, restarts, and `kubectl logs` / `describe`

**Done when:** app runs in Kind; same YAML is what you will take to AKS.

| Reading | Why | Status |
|---------|-----|--------|
| [Kubernetes components](https://kubernetes.io/docs/concepts/overview/components/) | Control plane vs nodes | New |
| [Kubernetes basics](https://kubernetes.io/docs/tutorials/kubernetes-basics/) | Pods, Deployments, Services | New |
| [Workload resources](https://kubernetes.io/docs/concepts/workloads/) | Rolling updates, crash loops | New |
| [Liveness / readiness probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/) | `/health` wiring | New |
| [ConfigMaps and Secrets](https://kubernetes.io/docs/concepts/configuration/) | Endpoint/key injection | New |
| [Kind quick start](https://kind.sigs.k8s.io/docs/user/quick-start/) | Local cluster + loading images | New |

---

### Phase 4 — AKS + Terraform

**Learn:** managed Kubernetes on Azure via **IaC**; reuse Kind manifests; cost hygiene.

- [ ] Terraform in `infra/`: resource group + small AKS (cheap node SKU; destroy when done)
- [ ] `terraform apply` → `az aks get-credentials` (or output kubeconfig); apply the **same** `deploy/k8s/` manifests
- [ ] Image from ACR (or documented pull path); Secret for OpenAI
- [ ] Ingress **or** LoadBalancer **or** port-forward for demo access
- [ ] Document create / destroy and cost notes in `docs/runbook.md`

**Done when:** documented URL (or port-forward steps) hits chat on AKS; `terraform destroy` is practiced.

| Reading | Why | Status |
|---------|-----|--------|
| [Why IaC / Terraform intro](https://developer.hashicorp.com/terraform/intro) · [azurerm provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs) | Repeatable RG + destroy habit | Known (AKS types are New) |
| [AKS intro](https://learn.microsoft.com/azure/aks/intro-kubernetes) | Shared responsibility / node pools | New |
| [AKS with Terraform](https://learn.microsoft.com/azure/aks/learn/quick-kubernetes-deploy-terraform) | Lab cluster IaC | Known Terraform; **New** AKS |
| [Deploy AKS with Azure CLI](https://learn.microsoft.com/azure/aks/learn/quick-kubernetes-deploy-cli) | kubectl context / credentials | New |
| [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/) | LoadBalancer vs Ingress vs port-forward | New |
| [ACR + AKS auth](https://learn.microsoft.com/azure/aks/cluster-container-registry-integration) | Pull images cleanly | New |
| [AKS cost best practices](https://learn.microsoft.com/azure/aks/best-practices-cost) | Why destroy between demos | New |

Keyless identity is **Phase 6** (do not block Phase 4 on it).

---
### Phase 5 — Thin CI

**Learn:** gate on tests; build the image; optional AKS deploy when the cluster exists.

- [ ] GitHub Actions: pytest (mocked OpenAI) on PR/push
- [ ] Build (and optionally push) image to ACR
- [ ] Optional: deploy to AKS via `workflow_dispatch` only (cluster may be destroyed)

**Done when:** CI runs tests and builds an image; failed tests block the pipeline.

| Reading | Why | Status |
|---------|-----|--------|
| [GitHub Actions — deploying](https://docs.github.com/en/actions/deployment/about-deployments/about-continuous-deployment) | Gated CD vocabulary | Known |
| [GitHub Actions for AKS](https://learn.microsoft.com/azure/aks/kubernetes-action) | Build → push → deploy pattern | New |
| [Azure/k8s-deploy](https://github.com/Azure/k8s-deploy) | Optional manifest rollout | New |

---

## Advanced phases (after 0–5)

Only after the Docker → Kind → Terraform/AKS → CI path is demo-ready. Keep each phase **thin**.

### Phase 6 — Workload Identity & secrets

**Learn:** keyless pod → Azure OpenAI; tighten secret handling.

**Why:** Long-lived API keys in Secrets are a weak demo story. Workload Identity is what production AKS + Azure AI setups aim for, and it differentiates this project from “I put a key in an env var.” Complements Docker/K8s without overlapping work observability.

- [ ] Enable workload identity on the lab AKS (Terraform or documented steps)
- [ ] Bind the proxy ServiceAccount to an identity that can call Azure OpenAI
- [ ] Remove (or stop requiring) the OpenAI API key Secret for the AKS deploy path
- [ ] Optional: NetworkPolicy denying egress except OpenAI/DNS
- [ ] Update `docs/runbook.md` with the identity story

**Done when:** chat on AKS works **without** an API key in the pod Secret; you can explain the identity chain in an interview.

| Reading | Why | Status |
|---------|-----|--------|
| [AKS workload identity](https://learn.microsoft.com/azure/aks/workload-identity-overview) | Pod → Entra identity | Known MI idea; **New** on AKS |
| [OpenAI + Managed Identity](https://learn.microsoft.com/azure/ai-services/openai/how-to/managed-identity) | Keyless calls to the model | New |
| [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/) | Optional egress lock-down | New |

---

### Phase 7 — Thin RAG

**Learn:** retrieve-then-generate with a tiny doc set behind the same proxy.

**Why:** Interviewers often ask how grounded answers work. A small RAG path shows AI systems design on top of your K8s proxy — without turning the repo into a search-product or needing dashboards.

- [ ] Ingest a tiny doc set (Azure AI Search **or** embedded vectors — pick one)
- [ ] `/v1/chat` (or `/v1/chat/rag`) retrieves context, then calls Azure OpenAI
- [ ] Document limits: corpus size, failure mode when retrieval misses
- [ ] Tests: mock retrieval + model (no live spend in CI)

**Done when:** a question that needs the docs answers with grounded content; a question outside the docs behaves safely (refuse or say unknown).

| Reading | Why | Status |
|---------|-----|--------|
| [RAG solution design](https://learn.microsoft.com/azure/architecture/ai-ml/guide/rag/rag-solution-design-and-evaluation-guide) | Retrieve → generate pattern | New |
| [Azure AI Search + RAG](https://learn.microsoft.com/azure/search/retrieval-augmented-generation-overview) | Hosted retrieval option | New |

---

### Phase 8 — Thin evals (quality gate)

**Learn:** golden prompts, baseline score, fail CI on quality drop.

**Why:** This is the SDET / AI-quality angle — different from observability. You already gate on unit tests; evals gate on **behavior**. One intentional regression failing CI is enough for the portfolio story.

- [ ] `tests/evals/golden_cases.json` (15–30 cases)
- [ ] Scorers: contains / not_contains (keep simple)
- [ ] Actions job (nightly or on main) — mocked policy **or** cheap staging; no surprise token spend
- [ ] Fail pipeline if score < baseline; document flake policy

**Done when:** one intentional bad prompt/change fails CI; README explains the gate.

| Reading | Why | Status |
|---------|-----|--------|
| [Eval approach for generative AI](https://learn.microsoft.com/azure/ai-foundry/concepts/evaluation-approach-gen-ai) | Quality as a pipeline signal | New |
| [OpenAI Evals guide](https://platform.openai.com/docs/guides/evals) | Golden-set vocabulary | New |

---

### Phase 9 — GitOps

**Learn:** cluster desired state from git (Argo CD or Flux — pick one).

**Why:** Phase 5 pushes an image; GitOps answers “how does the cluster stay aligned with the repo?” Strong platform signal next to Terraform/AKS, and still separate from metrics/dashboards.

- [ ] Install Argo CD **or** Flux on the lab AKS
- [ ] Point it at `deploy/k8s/` (or a render of it); sync the proxy
- [ ] Demo: change a manifest in git → cluster updates (or show sync UI + `kubectl`)
- [ ] Document: GitOps vs `workflow_dispatch` kubectl apply

**Done when:** a git change is the source of truth for the proxy Deployment on AKS (lab cluster).

| Reading | Why | Status |
|---------|-----|--------|
| [GitOps principles](https://opengitops.dev/) | Desired state in git | New |
| [Flux on AKS](https://learn.microsoft.com/azure/azure-arc/kubernetes/tutorial-use-gitops-flux2) | One Azure-friendly path | New |
| [Argo CD getting started](https://argo-cd.readthedocs.io/en/stable/getting_started/) | Alternate popular controller | New |

---

## Skills → resume mapping

| Phase | Skills to claim |
|-------|-----------------|
| 0–1 | FastAPI, Azure OpenAI, mocked tests |
| 2 | Docker, containerized Python API |
| 3 | Kubernetes primitives, probes, Secrets (Kind) |
| 4 | AKS, Terraform, cloud cost hygiene |
| 5 | CI for containerized apps |
| 6 | AKS Workload Identity, keyless AI auth |
| 7 | Thin RAG on a K8s-hosted proxy |
| 8 | AI eval / quality gating in CI |
| 9 | GitOps (Argo CD or Flux) |

---

## Suggested pace

| Weeks | Focus |
|-------|--------|
| 1 | Phase 0–1 (stub → Azure OpenAI) |
| 2 | Phase 2 (Docker) |
| 3–4 | Phase 3 (Kind — main K8s learning) |
| 5–6 | Phase 4 (Terraform + AKS) |
| 7 | Phase 5 (thin CI) + polish README / demo script |
| Later | Advanced 6 → 7 → 8 → 9 (one at a time) |

Destroy AKS when not demoing — node pools dominate cost.

---

## Demo script (for interviews)

1. Architecture: client → container on K8s → Azure OpenAI (30s)  
2. Show Dockerfile + `deploy/k8s/` + Terraform `infra/`  
3. Kind or AKS: `curl /health` + `curl /v1/chat`  
4. `kubectl get pods` / logs  
5. CI: pytest + image build  
6. `terraform destroy` cost note  
7. Optional: Workload Identity, RAG answer, eval gate, or GitOps sync  

---

## Prerequisites

- Azure subscription (Azure OpenAI + AKS)  
- Docker Desktop (or equivalent)  
- kubectl, Kind, Terraform, Azure CLI (`az login`)  
- Python 3.13+  
- GitHub repo for Actions  

**Readings** live under each phase (**Known** = refresher; **New** = focus). Skim one **New** overview per phase, then build.

---

## Progress checklist (roll-up)

| Phase | Status | Notes |
|-------|--------|-------|
| 0 — Skeleton | Done | Local stub `/health` + `/v1/chat`; pytest green |
| 1 — Azure OpenAI | Not started | |
| 2 — Docker | Not started | |
| 3 — Kind (local K8s) | Not started | Main K8s learning |
| 4 — AKS + Terraform | Not started | Same manifests as Kind |
| 5 — Thin CI | Not started | |
| 6 — Workload Identity | Deferred | Advanced |
| 7 — Thin RAG | Deferred | Advanced |
| 8 — Thin evals | Deferred | Advanced |
| 9 — GitOps | Deferred | Advanced |
