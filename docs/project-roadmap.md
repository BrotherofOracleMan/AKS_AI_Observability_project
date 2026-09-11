# Project Roadmap: AI on Kubernetes

Learning-focused guide. Hero skills: **Docker + Kubernetes + AI**. Heavy observability is out of scope — thin logs + `kubectl` only.

**One sequence — do not skip ahead or jump around.** Finish each phase’s “Done when” before the next.

```text
0 Skeleton → 1 Azure OpenAI → 2 Docker → 3 Kind → 4 CI → 5 Evals → 6 AKS → Interview polish
                                                              ↓
                                                    deferred (identity, RAG, GitOps, Go)
```

**You are here:** Phase **4 — Thin CI** (Phases 0–3 done).

---

## What this project is

A small FastAPI **LLM proxy** (`/health`, `/v1/chat`) between clients and **Azure OpenAI**:

```text
Client  -->  FastAPI (container on K8s)  -->  Azure OpenAI
                    ↑
         Docker image + K8s manifests
         (Kind first → CI/evals → AKS)
```

**Interview one-liner:** “I automated quality for an AI API — mocked pytest in CI, Kind smoke tests, golden-prompt evals, then the same image on AKS with Terraform.”

---

## Goals / non-goals

**Goals:** API proxy → Docker → Kind + smoke → CI merge gates → eval gate → AKS with Terraform (same manifests).

**Non-goals:** Heavy Monitor/Prometheus portfolios, GPU pools, service mesh, fine-tuning, multi-cluster.

Deferred (after Phase 6): Workload Identity, thin RAG, GitOps, optional Go — [deferred-phases.md](deferred-phases.md).

---

## Suggested repo layout

```
ai-on-kubernetes/
  README.md
  docs/project-roadmap.md   # this file
  docs/deferred-phases.md
  docs/runbook.md           # Phase 6 — AKS create/destroy
  src/                      # FastAPI app
  tests/                    # test_mock.py, test_smoke.py, evals/ (Phase 5)
  deployments/k8/           # Kind + AKS manifests
  infra/                    # Terraform (Phase 6)
  .github/workflows/        # Phase 4
  probe_smoke.sh            # Kind live smoke
  Dockerfile
  pyproject.toml
```

---

## Thin ops (minimal)

| Signal | How |
|--------|-----|
| Request / latency / tokens | Structured logs from the proxy |
| Pod health | `kubectl get/describe/logs` |
| Provider errors | Log status; keep quotas low |

---

## Phased plan (sequential)

Mark `[x]` as you finish. Readings: **Known** = refresher; **New** = focus.

### Phase 0 — Repo + local API skeleton ✅

**Learn:** project layout, health, stub chat.

- [x] Git repo; Python 3.13 + uv; FastAPI
- [x] `GET /health`, `POST /v1/chat` stub + Pydantic
- [x] `.env.example`; pytest; local README

**Done when:** `uvicorn` locally + pytest green with no Azure.

---

### Phase 1 — Azure OpenAI integration ✅

**Learn:** deployments, keys, token usage; mocked tests for CI later.

- [x] Foundry / Azure OpenAI + `gpt-4.1-mini`
- [x] Real client + structured logs (request id, latency, tokens)
- [x] Unit tests with **mocked** OpenAI (`mocker.patch("main.chat")`)

**Done when:** local curl hits Azure; mocks cover CI path.

| Reading | Status |
|---------|--------|
| [Azure OpenAI concepts](https://learn.microsoft.com/azure/ai-services/openai/concepts/models) | Known |
| [Python quickstart](https://learn.microsoft.com/azure/ai-services/openai/chatgpt-quickstart) | Known |

---

### Phase 2 — Docker ✅

**Learn:** image vs container; runtime env injection (not baked secrets).

- [x] `Dockerfile` + `.dockerignore` + `requirements.txt`
- [x] Local `docker run --env-file` smoke (`/health` + chat)

**Done when:** containerized proxy works locally with env-injected Azure config.  
**Not in this phase:** push to ACR — that moves to **Phase 6** (AKS needs a registry; Kind uses `kind load`).

| Reading | Status |
|---------|--------|
| [Docker overview](https://docs.docker.com/get-started/docker-overview/) | Known |

**Mental model (revisit at Interview polish):** image = blueprint; container = running instance; shares host kernel (lighter than a VM).

---

### Phase 3 — Kubernetes locally (Kind) ✅

**Learn:** Deployment, Service, probes, Secret; main K8s learning phase.

- [x] Kind + `deployments/k8/` (Deployment, Service, probes, Secret)
- [x] Image load; port-forward `/health` + `/v1/chat`
- [x] Learning drills (selector, image typo, delete/re-apply, probes, rewrite Service)
- [x] Smoke: `./probe_smoke.sh` → `pytest -m live` (port-forward first)

**Done when:** app runs in Kind; smoke is scripted.

| Reading | Status |
|---------|--------|
| [K8s basics](https://kubernetes.io/docs/tutorials/kubernetes-basics/) | New |
| [Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/) | New |
| [Kind quick start](https://kind.sigs.k8s.io/docs/user/quick-start/) | New |

See [deployments/k8/README.md](../deployments/k8/README.md).

---

### Phase 4 — Thin CI ← **you are here**

**Learn:** merge gates; build the same image without needing AKS.

- [ ] GitHub Actions on PR/push: pytest **mocked only** (`-m "not live"` or `tests/test_mock.py`)
- [ ] `docker build` in CI (no registry push)
- [ ] Failed tests block the pipeline

**Done when:** CI runs mocked tests + builds an image; red tests fail the workflow.

**Does not require AKS.** Live Kind smoke stays local (`./probe_smoke.sh`).

| Reading | Status |
|---------|--------|
| [GitHub Actions — deployments overview](https://docs.github.com/en/actions/deployment/about-deployments/about-continuous-deployment) | Known |

---

### Phase 5 — Thin evals (quality gate)

**Learn:** golden prompts; fail CI on quality drop (after CI exists so the gate has somewhere to run).

- [ ] `tests/evals/golden_cases.json` (15–30 cases)
- [ ] Simple scorers (contains / not_contains)
- [ ] CI job (nightly or on main) — mocked or cheap; no surprise spend
- [ ] Fail if score < baseline; document flake policy

**Done when:** one intentional regression fails CI; README explains the gate.

| Reading | Status |
|---------|--------|
| [Eval approach for generative AI](https://learn.microsoft.com/azure/ai-foundry/concepts/evaluation-approach-gen-ai) | New |

---

### Phase 6 — AKS + Terraform

**Learn:** managed K8s via IaC; reuse Kind manifests; cost hygiene. Needs a **registry** (ACR) — AKS cannot see your laptop Docker daemon.

- [ ] Push image to ACR (`docker tag` + `docker push`); fix Entra / `AcrPush` (prefer not relying on admin password)
- [ ] Terraform in `infra/`: RG + small AKS (cheap SKU; destroy when idle)
- [ ] `terraform apply` → kubeconfig; apply same `deployments/k8/` (ACR image; drop `imagePullPolicy: Never`)
- [ ] Attach ACR ↔ AKS pull auth
- [ ] Ingress **or** LoadBalancer **or** port-forward for demo
- [ ] `docs/runbook.md` create/destroy + cost notes
- [ ] Reuse `./probe_smoke.sh` / live tests against the AKS URL or tunnel

**Done when:** chat works on AKS; `terraform destroy` practiced.

| Reading | Status |
|---------|--------|
| [ACR intro](https://learn.microsoft.com/azure/container-registry/container-registry-intro) | Known |
| [AKS + Terraform](https://learn.microsoft.com/azure/aks/learn/quick-kubernetes-deploy-terraform) | New |
| [ACR + AKS auth](https://learn.microsoft.com/azure/aks/cluster-container-registry-integration) | New |
| [AKS cost best practices](https://learn.microsoft.com/azure/aks/best-practices-cost) | New |

Keyless identity → [deferred-phases.md](deferred-phases.md) (after this phase).

---

### Interview polish (after Phase 6)

- [ ] Recruiter pitch: image vs container vs VM (~1 min)
- [ ] Walk the demo script once without notes
- [ ] Refresh README status + 3–5 resume bullets
- [ ] Optional: `docs/architecture.md`

**Pitch:**

> “A container packages my app and its dependencies so it runs the same way on my laptop, in CI, and on Kubernetes. It’s lighter than a VM because it shares the host OS kernel. An image is the blueprint; a container is a running instance. I put an LLM proxy in an image, inject Azure secrets at runtime, and run that same image on Kind and AKS.”

---

## Pace (same order as phases)

| When | Phase |
|------|--------|
| Done | 0–3 |
| **Now** | **4 — Thin CI** |
| Next | 5 — Evals |
| Then | 6 — AKS + Terraform |
| Then | Interview polish |
| Later | [deferred-phases.md](deferred-phases.md) |

Destroy AKS when not demoing — node pools dominate cost.

---

## Demo script (interviews)

1. Architecture: client → container on K8s → Azure OpenAI (30s)
2. Dockerfile + `deployments/k8/` (+ `infra/` after Phase 6)
3. Kind (or AKS): `/health` + `/v1/chat`; `./probe_smoke.sh`
4. `kubectl get pods` / logs
5. CI: mocked pytest + image build (+ eval gate after Phase 5)
6. After Phase 6: `terraform destroy` cost note

---

## Resume bullets (fill as you finish)

1. ✅ Automated API tests — mocked Azure OpenAI (no token spend in default pytest).
2. ✅ Kind post-deploy smoke — `./probe_smoke.sh` / `pytest -m live`.
3. [ ] CI on every PR — pytest gates merge; builds container image.
4. [ ] LLM eval gate — golden prompts; pipeline fails on quality regression.
5. [ ] Same manifests on AKS via Terraform; destroy when idle.

---

## Prerequisites

- Azure subscription (OpenAI; AKS in Phase 6)
- Docker Desktop, kubectl, Kind
- Terraform + `az` (Phase 6)
- Python 3.13+, GitHub repo (Phase 4)

---

## Progress checklist

| Phase | Status | Notes |
|-------|--------|-------|
| 0 — Skeleton | **Done** | Local API + pytest |
| 1 — Azure OpenAI | **Done** | Live chat + mocks |
| 2 — Docker | **Done** | Local image + `docker run` smoke (ACR push → Phase 6) |
| 3 — Kind | **Done** | Manifests + `./probe_smoke.sh` |
| 4 — Thin CI | **Next** | Mocked pytest + `docker build` (no ACR) |
| 5 — Thin evals | Not started | After CI |
| 6 — AKS + Terraform | Not started | ACR push + AKS pull + Terraform |
| Interview polish | Later | After Phase 6 |
| Deferred | Later | [deferred-phases.md](deferred-phases.md) |
