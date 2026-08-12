# Project Roadmap: AI on Kubernetes

Learning-focused guide for the portfolio project described below.

Hero skills: **Docker + Kubernetes + AI**. Heavy observability is **out of scope** (covered at work) — keep only thin logs + `kubectl`.

---

## What this project is

A small FastAPI **LLM proxy** (`/health`, `/v1/chat`) that sits between clients and **Azure OpenAI**:

```text
Client  -->  FastAPI (container on K8s)  -->  Azure OpenAI
                    ↑
         Docker image + K8s manifests
         (Kind first → Terraform AKS)
```

Clients call *your* API; you forward the prompt to a hosted model and return the reply. That middle layer is where you add real service habits (config, logs, identity, tests, deploy).

**The point:** prove you can run **AI inference as a real workload on Kubernetes** — not as a one-off script or **Jupyter notebook** experiment (interactive cells you run by hand, with no image, cluster, or CI).

**Interview one-liner:** “I containerized an LLM proxy, ran it on Kubernetes locally, then on AKS with Terraform — keyless identity, plus thin RAG, evals, and GitOps.”

**Core path:** stub API → Azure OpenAI → Docker → Kind → Terraform/AKS → thin CI  

**Advanced (later):** Workload Identity → thin RAG → thin evals → GitOps  

---

## Goals / non-goals

### Goals (core — Phases 0–5)

- Ship a real **API proxy** in front of Azure OpenAI (not a one-off script or Jupyter notebook)
- **Dockerize** the app and run it with env-injected config
- Learn **Kubernetes primitives** on Kind (Deployment, Service, probes, Secret)
- Provision **AKS with Terraform** and deploy the **same** manifests; destroy when idle
- **Thin ops only:** structured logs + basic token/request logging; `kubectl` for pod health
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

Core:   code → Docker → Kind → Terraform AKS
CI:     pytest (mocked OpenAI) → build/push image → optional deploy
Later:  Workload Identity | thin RAG | thin evals | GitOps
```

### Suggested repo layout (create as you go)

```
ai-on-kubernetes/
  README.md
  docs/
    project-roadmap.md      # this file
    architecture.md         # fill in after Kind/AKS
    runbook.md              # create/destroy AKS + debug pods + identity
  src/
    main.py                 # FastAPI /health + /v1/chat
    config.py               # pydantic-settings from .env
    openai_client.py        # AzureOpenAI chat helper
    models.py               # ChatRequest / ChatMessage
  tests/
    test_app.py
    evals/                  # optional Phase 8
  deploy/
    k8s/                    # Deployment, Service, probes, Secret examples
  infra/                    # Terraform (AKS, RG, …)
  .github/workflows/
  Dockerfile
  .dockerignore
  requirements.txt        # exported for the image build
  pyproject.toml
```


---

## Thin ops (intentionally minimal)

Not a portfolio observability project — depth lives at work. Here you only need enough to debug and talk cost:

| Signal | How you see it |
|--------|----------------|
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

- [x] Create Azure OpenAI / Foundry resource + chat deployment (`gpt-4.1-mini`)
- [x] Wire real client (`openai_client.py` / `config.py` / `models.py`)
- [x] Return model text + record `usage` tokens on each call
- [x] Structured logging: request id, latency_ms, tokens, status
- [x] Unit tests with **mocked** OpenAI (`mocker.patch("main.chat")` — no spend in CI)

**Done when:** local curl to `/v1/chat` hits Azure OpenAI; tests mock the provider. ✅

**Cost note:** set low quotas; never commit keys; destroy lab resources when idle.

| Reading | Why | Status |
|---------|-----|--------|
| [Azure OpenAI concepts](https://learn.microsoft.com/azure/ai-services/openai/concepts/models) | Deployments vs models; tokens → cost | Known |
| [Azure OpenAI quickstart (Python)](https://learn.microsoft.com/azure/ai-services/openai/chatgpt-quickstart) | First real chat call | Known |
| [Completions / SDK usage](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/completions) | Tokens in responses | Known |
| [Quotas & limits](https://learn.microsoft.com/azure/ai-services/openai/quotas-limits) | 429s, lab quotas | Known |
| [Azure OpenAI pricing](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/) | Token/$ intuition | Known |


---

### Phase 2 — Docker

**Build (compact):** ship one image of the FastAPI proxy; inject Azure config at **runtime**. Same image → Kind → AKS later.

**Learn (spend time here):** be able to explain a **container** to a recruiter without hand-waving. Kubernetes schedules containers — if you can’t explain the unit, the rest of the portfolio story wobbles.

#### Recruiter-ready mental model

Practice saying this out loud until it’s natural:

> “A **container** packages my app with its runtime dependencies so it runs the same way on my laptop, in CI, and on Kubernetes. It’s lighter than a VM: it shares the host OS kernel instead of booting a full guest OS. An **image** is the immutable blueprint (`docker build`); a **container** is a running instance of that image (`docker run`). In this project I put the LLM proxy in an image, pass Azure OpenAI secrets as env vars at runtime, and later Kubernetes runs that same image as pods.”

Know these distinctions cold:

| Term | Plain English |
|------|----------------|
| **Image** | Snapshot / template (filesystem + metadata + start command) |
| **Container** | Running process(es) created from an image |
| **Dockerfile** | Recipe to build the image |
| **Registry** (e.g. ACR) | Place to store/pull images (needed for AKS) |
| **VM** | Full machine + guest OS — heavier isolation, slower to start |
| **Container** | App + libs, shares host kernel — fast, portable |

**Why not just `uv run` on the server?**  
Deployments expect a standard artifact. K8s doesn’t SSH in and activate your venv — it pulls an image and starts a container.

**Optional depth (if you want extra confidence):** namespaces/cgroups at a high level (“isolation + resource limits”), image **layers** / cache, `-p 8000:8000` = publish container port to host.

#### Todos (keep short)

- [x] `Dockerfile` + `.dockerignore` + `requirements.txt` (no `.env` / `.venv` in the image)
- [x] Image runs uvicorn on `0.0.0.0:8000` (`CMD` with `--app-dir src`)
- [x] Smoke: `docker build` + `docker run --env-file .env -p …`; `curl` `/health` + `POST /v1/chat` (verified on host port 8001)
- [x] Push to ACR: `aiaksresourceregistry-….azurecr.io/ai-on-kubernetes:local`

**Done when:** containerized proxy works locally with env-injected Azure config. ✅  

(Recruiter “explain a container” polish is deferred to **Interview polish** at the end — keep shipping Kind/AKS first.)

**Interview one-liner (when you need it later):** “I containerized the LLM proxy — same image from local Docker to Kind to AKS — with Azure credentials injected at runtime, not baked into the image.”

**ACR note (lab):** Entra Guest + `az acr login` failed data-plane auth; push worked with **ACR admin** `docker login`. Portal “list repositories” may still fail under Entra — verify with admin CLI. Prefer admin/`--password-stdin`; rotate keys if pasted in shell history. Kind can still use `kind load docker-image` without ACR. **Fix Entra properly in Phase 4** (don’t block Kind).

#### Commands

```bash
docker build -t ai-on-kubernetes:local .
docker run --rm -p 8000:8000 --env-file .env ai-on-kubernetes:local

# ACR (after admin docker login)
docker tag ai-on-kubernetes:local \
  aiaksresourceregistry-e4a9a2d8eqd7dhck.azurecr.io/ai-on-kubernetes:local
docker push \
  aiaksresourceregistry-e4a9a2d8eqd7dhck.azurecr.io/ai-on-kubernetes:local
```

#### Pitfalls

- Don’t copy `.env` or host `.venv` into the image  
- Bind uvicorn to `0.0.0.0` (not only localhost) so `-p` works  
- Prefer tagged images (`:local` / git sha) over endless `:latest`  
- Subscription **Owner** ≠ ACR push — need **AcrPush** and/or admin login for data plane  

| Reading | Why | Status |
|---------|-----|--------|
| [What is a container?](https://learn.microsoft.com/dotnet/architecture/microservices/container-docker-introduction/) | Containers vs VMs (revisit in Interview polish) | Skim now / revisit later |
| [Docker overview](https://docs.docker.com/get-started/docker-overview/) | Image vs container vs Dockerfile | Known |
| [Dockerfile best practices](https://docs.docker.com/build/building/best-practices/) | Slim image, `.dockerignore`, layers | Known |
| [docker run](https://docs.docker.com/reference/cli/docker/container/run/) | `-p`, `--env-file` | Known |
| [ACR intro](https://learn.microsoft.com/azure/container-registry/container-registry-intro) | Private registry; tag/push/pull | Known |


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
- [ ] **Fix ACR Entra auth** (so admin password isn’t required): e.g. Member user or working `az acr login` + **AcrPush**; confirm Portal can list repos; then disable ACR admin user if you turned it on for the lab
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
| 8 | **Interview polish** — container pitch, demo script, resume bullets |
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

## Interview polish (end of core path)

Do this **after** Kind/AKS/CI — not as a Phase 2 blocker. You’ll explain containers better once you’ve run the same image on Kubernetes.

- [ ] Recruiter pitch: image vs container vs VM in under a minute (use the Phase 2 mental model above)
- [ ] Walk the demo script once end-to-end without notes
- [ ] Refresh README status + 3–5 resume bullets from what you actually shipped
- [ ] Optional: 1-page `docs/architecture.md` sketch

**Pitch to practice then:**

> “A container packages my app and its dependencies so it runs the same way on my laptop, in CI, and on Kubernetes. It’s lighter than a VM because it shares the host OS kernel. An image is the blueprint; a container is a running instance. I put an LLM proxy in an image, inject Azure secrets at runtime, and run that same image on Kind and AKS.”

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
| 0 — Skeleton | Done | Local `/health` + `/v1/chat`; pytest green |
| 1 — Azure OpenAI | Done | Foundry + `gpt-4.1-mini`; live chat; logs; mocked tests |
| 2 — Docker | Done | Image smoke-tested + pushed to ACR (`…/ai-on-kubernetes:local`); pitch deferred |
| 3 — Kind (local K8s) | Not started | **Next** — main K8s learning |
| 4 — AKS + Terraform | Not started | Same manifests as Kind; includes ACR Entra auth fix |
| 5 — Thin CI | Not started | |
| 6 — Workload Identity | Deferred | Advanced |
| 7 — Thin RAG | Deferred | Advanced |
| 8 — Thin evals | Deferred | Advanced |
| 9 — GitOps | Deferred | Advanced |
| Interview polish | Deferred | After core path — container pitch + demo |
