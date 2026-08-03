# Project Roadmap: AKS AI Observability

Learning-focused guide for a portfolio project: deploy a FastAPI **Azure OpenAI proxy** on **AKS**, observe it like production software, and optionally gate deploys with a small **eval suite**.

---

## North star

```text
Client  -->  FastAPI on AKS  -->  Azure OpenAI
                |                    |
                +-- metrics/logs ----+
                |
           CI evals (golden prompts) can fail the pipeline
```

**Interview one-liner:** “I ran an LLM behind Kubernetes with latency/cost/error monitoring, and CI quality gates so regressions don’t ship.”

---

## Goals / non-goals

### Goals

- Ship a real **inference wrapper** (not a notebook)
- Run it on **AKS** (not only App Service)
- Emit and dashboard **request + token + cost** signals
- Alert on a few SLOs (errors, latency, cost/429 spike)
- Keep a **thin SDET chapter**: golden-prompt evals in CI
- Document architecture + runbooks in-repo

### Non-goals (v1)

- Training custom models / fine-tuning
- Full RAG product (can be a later phase)
- Multi-cluster, service mesh, GPU nodes
- Building a Promptfoo competitor
- Deep ML theory

---

## Target architecture

```
┌─────────────────┐     ┌──────────────────────────┐     ┌─────────────────┐
│  Client / CI    │────▶│  FastAPI (Deployment)    │────▶│  Azure OpenAI   │
│  curl, pytest   │     │  /health  /v1/chat       │     │  chat + tokens  │
└─────────────────┘     │  OTel metrics/logs       │     └─────────────────┘
                        └────────────┬─────────────┘
                                     │
                                     ▼
                        ┌──────────────────────────┐
                        │  Azure Monitor / AMP     │
                        │  dashboards + alerts     │
                        └──────────────────────────┘

Infra: Terraform → RG + AKS (+ ACR optional)
CI:    test → (eval) → build image → deploy to AKS
```

### Suggested repo layout (create as you go)

```
aks-ai-observability/
  README.md
  docs/
    project-roadmap.md      # this file
    architecture.md         # fill in after Phase 1–2
    runbook.md              # alerts + how to debug
  src/
    main.py                 # FastAPI app
    openai_client.py        # Azure OpenAI calls
    metrics.py              # counters / histograms
    config.py               # env settings
  go/                       # optional Phase G (proxy or CLI)
  tests/
    test_health.py
    test_chat_unit.py       # mocked OpenAI
    evals/
      golden_cases.json
      test_golden_evals.py  # optional Phase E
  deploy/
    k8s/                    # Deployment, Service, Ingress, probes
  infra/                    # Terraform (AKS, RG, …)
  .github/workflows/
  Dockerfile
  pyproject.toml / requirements.txt
```

---

## What you will monitor

### API (your service)

| Signal | Why |
|--------|-----|
| Request rate | Traffic / load |
| Error rate (4xx/5xx) | Availability |
| Latency p50 / p95 / p99 | SLO / UX |
| In-flight / concurrency | Saturation |

### Model / Azure OpenAI

| Signal | Why |
|--------|-----|
| Prompt + completion tokens | Cost drivers |
| Estimated $ per request / per hour | FinOps story |
| Provider errors (429, 5xx, content filter) | Capacity / safety |
| Model / deployment name | Debugging config drift |
| Time-to-first-token (if streaming) | Streaming UX |

### Kubernetes

| Signal | Why |
|--------|-----|
| Pod restarts / crash loops | Bad deploys / OOM |
| CPU / memory | Rightsizing |
| Ready replicas / HPA events | Scaling behavior |

### Starter alerts (pick 3)

1. Error rate > threshold for N minutes  
2. p95 latency > budget  
3. 429 storm **or** token/$ burn spike  

---

## Phased plan

Mark items `[x]` as you finish. Stay on one phase until the “done when” bar is met.

**Readings:** each phase has a quick-reference table. **Known** = already familiar (refresher); **New** = focus study time. Prefer Microsoft Learn + project docs for interview vocabulary.

### Phase 0 — Repo + local API skeleton

**Learn:** project layout, settings via env, health endpoint.

- [ ] Create git repo; Python 3.13 + uv/pip; FastAPI app
- [ ] `GET /health` → `{"status":"ok"}`
- [ ] `POST /v1/chat` stub (echo or fake response) with Pydantic schemas
- [ ] `.env.example` (no secrets in git)
- [ ] Basic pytest for health + schema validation
- [ ] README: how to run locally

**Done when:** `uvicorn` locally + pytest green with no Azure yet.

| Reading | Why | Status |
|---------|-----|--------|
| [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/) | App layout, Pydantic, DI | Known |
| [Settings / env](https://fastapi.tiangolo.com/advanced/settings/) | Config without secrets in code | Known |
| [Twelve-Factor — Config](https://12factor.net/config/) | Same env pattern locally → AKS | Known |
| [httpx / TestClient testing](https://fastapi.tiangolo.com/tutorial/testing/) | pytest for the proxy | Known |
| [LLM / AI gateway pattern](https://learn.microsoft.com/azure/api-management/azure-openai-api-from-specification) | Why a thin FastAPI front door (not chat UI) | New |

---

### Phase 1 — Azure OpenAI integration

**Learn:** Azure OpenAI (or AI Foundry) deployments, keys/identity, token usage in responses.

- [ ] Create Azure OpenAI resource + chat deployment (cheapest suitable model)
- [ ] Wire real client in `openai_client.py` (API key locally; prefer Managed Identity later on AKS)
- [ ] Return model text + record `usage` tokens on each call
- [ ] Structured logging: request id, latency_ms, tokens, status
- [ ] Unit tests with **mocked** OpenAI (no spend in CI)

**Done when:** local curl to `/v1/chat` hits Azure OpenAI; CI tests mock the provider.

**Cost note:** set low quotas; never commit keys; destroy lab resources when idle.

| Reading | Why | Status |
|---------|-----|--------|
| [Azure OpenAI concepts](https://learn.microsoft.com/azure/ai-services/openai/concepts/models) | Deployments vs models; tokens → cost/capacity | New |
| [Azure OpenAI quickstart (Python)](https://learn.microsoft.com/azure/ai-services/openai/chatgpt-quickstart) | First real chat call + deployment names | New |
| [Completions / SDK usage](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/completions) | Tokens in responses, chat shape | New |
| [Quotas & limits](https://learn.microsoft.com/azure/ai-services/openai/quotas-limits) | 429s, lab quotas, bill spikes | New |
| [Azure OpenAI pricing](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/) | Token/$ intuition for logging | New |

---

### Phase 2 — Containerize

**Learn:** Docker multi-stage or slim image, non-root user, 12-factor config.

- [ ] `Dockerfile` runs uvicorn
- [ ] Run container locally with env vars
- [ ] Optional: push to **Azure Container Registry (ACR)**

**Done when:** `docker run` serves `/health` and chat with env-injected secrets.

| Reading | Why | Status |
|---------|-----|--------|
| [What is a container?](https://learn.microsoft.com/dotnet/architecture/microservices/container-docker-introduction/) | Containers vs VMs mental model | Known |
| [Docker best practices](https://docs.docker.com/build/building/best-practices/) | Slim image, non-root, layer caching | Known basics; **New** for shipping the API |

---

### Phase 3 — Kubernetes locally (Kind / minikube)

**Learn:** Deployment, Service, probes, ConfigMap/Secret — before paying for AKS.

- [ ] Kind or minikube cluster
- [ ] Manifests: Deployment + Service + liveness/readiness on `/health`
- [ ] Secret for OpenAI endpoint/key (or skip real calls in local K8s)
- [ ] `kubectl port-forward` smoke test

**Done when:** app runs in local K8s; you can explain probes and restarts.

| Reading | Why | Status |
|---------|-----|--------|
| [Kubernetes components](https://kubernetes.io/docs/concepts/overview/components/) | Control plane vs nodes | New |
| [Kubernetes basics](https://kubernetes.io/docs/tutorials/kubernetes-basics/) | Pods, Deployments, Services | New |
| [Workload resources](https://kubernetes.io/docs/concepts/workloads/) | Rolling updates, crash loops | New |
| [Liveness / readiness probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/) | `/health` wiring for AKS later | New |
| [ConfigMaps and Secrets](https://kubernetes.io/docs/concepts/configuration/) | Endpoint/key injection | New |
| [Kind quick start](https://kind.sigs.k8s.io/docs/user/quick-start/) | Cheap local cluster | New |

---

### Phase 4 — AKS + Terraform

**Learn:** AKS basics, node pools, kubectl context, IaC for cluster.

- [ ] Terraform: resource group + AKS (small node SKU; destroy when done)
- [ ] Connect kubectl; deploy same manifests (or Helm later)
- [ ] Ingress **or** port-forward/LoadBalancer for demo access
- [ ] Document create / destroy costs in `docs/runbook.md`
- [ ] Prefer workload identity / MI for OpenAI over long-lived keys in Secrets (stretch)

**Done when:** public or documented URL hits chat on AKS; `terraform destroy` is practiced.

| Reading | Why | Status |
|---------|-----|--------|
| [Why IaC / Terraform intro](https://developer.hashicorp.com/terraform/intro) · [azurerm provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs) | Repeatable RG + destroy habit | Known (AKS types are New) |
| [AKS intro](https://learn.microsoft.com/azure/aks/intro-kubernetes) | Shared responsibility / node pools | New |
| [AKS with Terraform](https://learn.microsoft.com/azure/aks/learn/quick-kubernetes-deploy-terraform) | Lab cluster IaC | Known Terraform; **New** AKS |
| [Connect with kubectl](https://learn.microsoft.com/azure/aks/learn/quick-kubernetes-deploy-cli) | Context, smoke deploys | New |
| [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/) | LoadBalancer vs Ingress vs port-forward | New |
| [AKS workload identity](https://learn.microsoft.com/azure/aks/workload-identity-overview) | Pod MI stretch goal | Known MI; **New** on AKS |
| [OpenAI + Managed Identity](https://learn.microsoft.com/azure/ai-services/openai/how-to/managed-identity) | Keyless pod → OpenAI | New |
| [AKS cost best practices](https://learn.microsoft.com/azure/aks/best-practices-cost) | Why destroy between demos | New |

---

### Phase 5 — Observability (core of the portfolio)

**Learn:** RED metrics + AI-specific tokens/cost; Azure Monitor or Prometheus path.

- [ ] Emit metrics: request count, errors, latency histogram, tokens, estimated cost
- [ ] Export via OpenTelemetry → Azure Monitor **or** Managed Prometheus
- [ ] One dashboard (Workbook or Grafana): latency, errors, tokens/$  
- [ ] Three alerts wired (email/Teams/Action Group is enough)
- [ ] `docs/architecture.md` + short incident-style notes in `runbook.md`

**Done when:** you can show a live dashboard and describe what each alert means.

| Reading | Why | Status |
|---------|-----|--------|
| [OpenTelemetry concepts](https://opentelemetry.io/docs/concepts/observability-primer/) | Metrics + logs (+ traces) pillars | New |
| [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/) | Instrument the proxy | New |
| [Azure Monitor OTel Distro](https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-enable) | Shortest path into Azure | New |
| [Managed Prometheus on AKS](https://learn.microsoft.com/azure/azure-monitor/containers/prometheus-metrics-overview) | Prom/Grafana alternative | New |
| [RED method](https://grafana.com/blog/2022/04/20/the-red-method-how-to-instrument-your-services/) | Rate, Errors, Duration for `/v1/chat` | New |
| [SRE — Service Level Objectives](https://sre.google/sre-book/service-level-objectives/) | SLIs/SLOs → alert intent | New |
| [USE method](https://www.brendangregg.com/usemethod.html) | CPU/memory/restarts saturation | New |
| [GenAI / Foundry metrics](https://learn.microsoft.com/azure/ai-foundry/observability/concepts/ai-foundry-metrics) | Tokens, cost, filter/provider errors | New |
| [Azure Monitor alerts](https://learn.microsoft.com/azure/azure-monitor/alerts/alerts-overview) | Action Groups + starter SLOs | New |

---

### Phase 6 — CI/CD

**Learn:** gated pipeline to AKS.

- [ ] GitHub Actions: pytest (mocked OpenAI) on PR/push
- [ ] Build/push image to ACR
- [ ] Deploy to AKS only if tests pass
- [ ] Disable auto-deploy when cluster is destroyed (workflow_dispatch only)

**Done when:** merge → tests → image → rollout; failed tests block deploy.

| Reading | Why | Status |
|---------|-----|--------|
| [GitHub Actions — deploying](https://docs.github.com/en/actions/deployment/about-deployments/about-continuous-deployment) | Gated CD vocabulary | Known |
| [GitHub Actions for AKS](https://learn.microsoft.com/azure/aks/kubernetes-action) | Build → push → deploy | New |
| [Azure/k8s-deploy](https://github.com/Azure/k8s-deploy) | Manifest rollout from Actions | New |
| [ACR + AKS auth](https://learn.microsoft.com/azure/aks/cluster-container-registry-integration) | Pull images cleanly | New |

---

### Phase E — Eval chapter (SDET differentiator, keep thin)

**Learn:** golden prompts, baselines, failing CI on quality drop.

- [ ] `tests/evals/golden_cases.json` (15–30 cases)
- [ ] Scorers: contains / not_contains / optional JSON schema
- [ ] Job in Actions (nightly or on main) that calls **staging** or a mocked policy
- [ ] Fail pipeline if score < baseline
- [ ] Document flake policy (retries, quarantine)

**Done when:** one intentional bad prompt change fails CI; README explains the gate.

| Reading | Why | Status |
|---------|-----|--------|
| [Eval approach for generative AI](https://learn.microsoft.com/azure/ai-foundry/concepts/evaluation-approach-gen-ai) | Quality as a pipeline signal | New |
| [OpenAI Evals guide](https://platform.openai.com/docs/guides/evals) | Golden-set / scoring vocabulary | New |
| [Promptfoo intro](https://www.promptfoo.dev/docs/intro/) | Optional local harness inspiration | New |

---

### Phase F (optional later) — Light RAG

Only after Phases 0–6 feel solid.

- [ ] Ingest a tiny doc set (AI Search or pgvector)
- [ ] `/v1/chat` retrieves then answers
- [ ] Extend evals for groundedness (“must cite” / must not invent)

| Reading | Why | Status |
|---------|-----|--------|
| [RAG solution design & evaluation](https://learn.microsoft.com/azure/architecture/ai-ml/guide/rag/rag-solution-design-and-evaluation-guide) | Retrieve-then-generate; groundedness | New |
| [MLOps maturity (Azure)](https://learn.microsoft.com/azure/architecture/ai-ml/guide/mlops-v2) | Interview framing: inference + ops, not training | New |

---

### Phase G (optional later) — Go companion

Only after the Python proxy path (0–6) is demo-ready. Keep this **thin** — do not replace the FastAPI service as the main portfolio piece.

**Learn:** Go basics in a cloud-native shape (HTTP service or CLI) next to the same AKS/OpenAI story.

Pick **one** track:

**Track A — Tiny Go proxy** (same contract as Python)

- [ ] `go/` module: `GET /health`, `POST /v1/chat` calling Azure OpenAI
- [ ] Dockerfile + deploy alongside (or instead of) Python for a short comparison demo
- [ ] Reuse the same env/config knobs (endpoint, deployment, key or MI later)
- [ ] Note latency/token metrics parity (or deliberately thinner than Python)

**Track B — Go CLI client** (lighter)

- [ ] `go/` CLI: send a prompt to the running FastAPI service on AKS
- [ ] Flags for URL, API key, prompt; print reply + latency
- [ ] Optional: smoke job in CI that builds the CLI (no live OpenAI spend)

**Done when:** you can show a small Go artifact in-repo and explain why Go is common in the Kubernetes ecosystem — without diluting the Python + observability demo.

| Reading | Why | Status |
|---------|-----|--------|
| [Go tour](https://go.dev/tour/) | Language basics | New |
| [Creating a Go module](https://go.dev/doc/tutorial/create-module) | Module layout for `go/` | New |
| [net/http](https://pkg.go.dev/net/http) · [Writing Web Applications](https://go.dev/doc/articles/wiki/) | Track A: minimal HTTP service | New |
| [Azure OpenAI REST](https://learn.microsoft.com/azure/ai-services/openai/reference) | Same chat API from Go (HTTP or SDK) | New |
| [Command-line flags](https://pkg.go.dev/flag) | Track B: CLI knobs | New |

---

## Skills → resume mapping

| Phase | Skills to claim |
|-------|-----------------|
| 0–1 | FastAPI, Azure OpenAI, Python packaging, mocked tests |
| 2–3 | Docker, Kubernetes primitives, probes |
| 4 | AKS, Terraform, cloud cost hygiene |
| 5 | Observability, SLOs, token/cost metrics (MLOps-relevant) |
| 6 | CI/CD to Kubernetes |
| E | AI quality / eval gating (SDET → AI quality story) |
| G | Go HTTP service or CLI in a K8s-adjacent workflow (optional) |

---

## Suggested 8–12 week pace

| Weeks | Focus |
|-------|--------|
| 1 | Phase 0–1 |
| 2 | Phase 2–3 |
| 3–4 | Phase 4 (AKS + Terraform) |
| 5–6 | Phase 5 (dashboards + alerts) |
| 7 | Phase 6 (CI/CD) |
| 8 | Phase E + polish README / demo script |
| Later | Optional F (RAG) and/or G (Go companion) |

Destroy AKS when not demoing — node pools dominate cost.

---

## Demo script (for interviews)

1. Architecture diagram (30s)  
2. `curl /health` + `curl /v1/chat` on AKS  
3. Dashboard: spike latency or tokens with a quick load  
4. Show an alert rule definition  
5. Show CI: tests + (optional) eval gate failing on a bad commit  
6. `terraform destroy` / cost note — shows maturity  

---

## Prerequisites

- Azure subscription you can create AKS + Azure OpenAI in  
- Docker Desktop (or equivalent)  
- kubectl, Terraform, Azure CLI (`az login`)  
- Python 3.13+  
- GitHub repo for Actions  

**Readings** live under each phase in [Phased plan](#phased-plan) (**Known** = refresher; **New** = focus). Skim one **New** overview per phase, then build.

---

## Progress checklist (roll-up)

| Phase | Status | Notes |
|-------|--------|-------|
| 0 — Skeleton | Not started | |
| 1 — Azure OpenAI | Not started | |
| 2 — Docker | Not started | |
| 3 — Local K8s | Not started | |
| 4 — AKS + Terraform | Not started | |
| 5 — Observability | Not started | |
| 6 — CI/CD | Not started | |
| E — Evals | Not started | |
| F — RAG (optional) | Deferred | |
| G — Go companion (optional) | Deferred | |
