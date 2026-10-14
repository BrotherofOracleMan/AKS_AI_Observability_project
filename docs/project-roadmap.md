# Project Roadmap: AI on Kubernetes

Learning-focused guide. Hero skills: **Docker + Kubernetes + AI**. Heavy observability is out of scope — thin logs + `kubectl` only.

**One sequence — do not skip ahead or jump around.** Finish each phase’s “Done when” before the next.

```text
0 Skeleton → 1 Azure OpenAI → 2 Docker → 3 Kind → 4 CI → 5 Evals → 6 AKS
                                                              ↓
                                                    deferred (identity, RAG, GitOps, Go)
```

**Status:** Phases **0–6 done**. Architecture + how to explain it: [architecture.md](architecture.md). AKS commands: [runbook.md](runbook.md). Optional next steps: [deferred-phases.md](deferred-phases.md).

---

## What this project is

A small FastAPI **LLM proxy** (`/health`, `/v1/chat`) between clients and **Azure OpenAI**:

```text
Client  -->  FastAPI (container on K8s)  -->  Azure OpenAI
                    ↑
         Docker image + K8s manifests
         (Kind first → CI/evals → AKS)
```

The model runs in Azure OpenAI (Microsoft's hardware); we build and run the proxy layer. Full picture: [architecture.md](architecture.md).

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
  docs/architecture.md      # design, K8s concepts, how to explain it
  docs/deferred-phases.md
  docs/runbook.md           # AKS create → deploy → test → destroy
  src/                      # FastAPI app
  tests/                    # test_mock.py, test_smoke.py, test_evals.py (Phase 5)
  deployments/k8/           # Kind manifests + Kustomize base
  deployments/aks/          # Kustomize overlay for AKS (ACR image)
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

**Mental model:** image = blueprint; container = running instance; shares host kernel (lighter than a VM). More: [architecture.md](architecture.md#image-vs-container-vs-vm).

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

### Phase 4 — Thin CI ✅

**Learn:** merge gates; build the same image without needing AKS.

- [x] GitHub Actions on PR/push: pytest **mocked only** (`tests/test_mock.py` via `mock_test.yml`)
- [x] `docker build` in CI (`push: false`, tag `ai-on-kubernetes:ci` — no ACR)
- [x] Failed tests block the pipeline (`needs: test`; verified: failing mock run skipped build)

**Done when:** CI runs mocked tests + builds an image; red tests fail the workflow. ✅  

Verified green run: [Actions #34544850875](https://github.com/BrotherofOracleMan/AKS_AI_Observability_project/actions/runs/34544850875) (`test / test` + `build`).

**Does not require AKS.** Live Kind smoke stays local (`./probe_smoke.sh`).

| Reading | Status |
|---------|--------|
| [GitHub Actions — deployments overview](https://docs.github.com/en/actions/deployment/about-deployments/about-continuous-deployment) | Known |

---

### Phase 5 — Thin evals (quality gate) ✅

**Learn:** regression-test **known answers**, not open-ended creativity. Fail CI when scorers reject bad text.

**What this is:** clear-answer prompts → `contains` / `not_contains` → CI (mocked) + optional local live against Kind.

**What this is not:** Azure AI Foundry multi-evaluators.

```text
parametrized cases  →  mocked /v1/chat (TestClient)     →  pass_scorer  →  CI (-m "not live")
                    →  live httpx → BASE_URL (@pytest.mark.live) →  pass_scorer  →  local only
gate proofs         →  pass_scorer(bad text) must be False
```

**Checklist:**

- [x] `tests/test_evals.py` with `@pytest.mark.parametrize` (inline cases)
- [x] Cases: slug `id`, `messages`, `must_contain`, `must_not_contain` (tightened prompts)
- [x] Shared `pass_scorer()` (case-insensitive)
- [x] Gate proofs: missing required / forbidden present / happy path
- [x] Mocked Azure path via `TestClient` (no token spend)
- [x] Wired into CI (`mock_test.yml`: `pytest tests/ -m "not live"`)
- [x] README note: harness vs live
- [x] `@pytest.mark.live` golden path — `httpx` → `config.base_url` / Kind port-forward (`test_golden_test_cases_live`)

**Vs other tests:**

| Layer | Proves |
|-------|--------|
| `test_mock.py` | API wiring |
| `test_smoke.py` / `./probe_smoke.sh` | Deployed system reachable |
| `test_evals.py` (mocked) | Scorers + golden harness in CI |
| `test_evals.py` (`-m live`) | Real answer quality via running app |

**Done when:** harness + gate proofs in CI + live path available locally. ✅

| Reading | Status |
|---------|--------|
| [Eval approach for generative AI](https://learn.microsoft.com/azure/ai-foundry/concepts/evaluation-approach-gen-ai) | Skim vocabulary only |

---

### Phase 6 — AKS + Terraform ✅

**Learn:** managed K8s via IaC; reuse Kind manifests; cost hygiene. Needs a **registry** (ACR) — AKS cannot see your laptop Docker daemon.

Commands: [runbook.md](runbook.md).

- [x] Push image to ACR (`docker tag` + `docker push`); fix Entra / `AcrPush` (prefer not relying on admin password)
- [x] Terraform in `infra/`: RG + small AKS (cheap SKU; destroy when idle)
- [x] `terraform apply` → kubeconfig; apply same base manifests via Kustomize overlay `deployments/aks/` (ACR image; `imagePullPolicy: IfNotPresent`)
- [x] Attach ACR ↔ AKS pull auth
- [x] Port-forward for demo (public LoadBalancer deferred until API auth — [deferred-phases.md](deferred-phases.md#public-exposure--api-auth))
- [x] `docs/runbook.md` create/destroy + cost notes
- [x] Reuse `./probe_smoke.sh` / live tests against the AKS tunnel

**Done when:** chat works on AKS; `terraform destroy` practiced. ✅

| Reading | Status |
|---------|--------|
| [ACR intro](https://learn.microsoft.com/azure/container-registry/container-registry-intro) | Known |
| [AKS + Terraform](https://learn.microsoft.com/azure/aks/learn/quick-kubernetes-deploy-terraform) | New |
| [ACR + AKS auth](https://learn.microsoft.com/azure/aks/cluster-container-registry-integration) | New |
| [AKS cost best practices](https://learn.microsoft.com/azure/aks/best-practices-cost) | New |

Keyless identity → [deferred-phases.md](deferred-phases.md) (after this phase).

---

## Pace (same order as phases)

| When | Phase |
|------|--------|
| Done | 0–6 |
| Optional | [deferred-phases.md](deferred-phases.md) |

Destroy AKS when not demoing — node pools dominate cost.

---

## Demo script (interviews)

Run the live part on **Kind** (free, instant); talk through AKS. Full talk track, commands, and likely follow-up questions: [architecture.md](architecture.md#talking-about-it).

1. Architecture: client → proxy container on K8s → Azure OpenAI (30s)
2. Dockerfile + `deployments/k8/` + `deployments/aks/` overlay + `infra/`
3. Kind: port-forward → `/health` + `/v1/chat`; `./probe_smoke.sh`; live evals
4. `kubectl get pods` / logs
5. CI: mocked pytest + eval harness + image build
6. AKS: same image + base manifests via Terraform; `terraform destroy` cost note

---

## Resume bullets (fill as you finish)

1. ✅ Automated API tests — mocked Azure OpenAI (no token spend in default pytest).
2. ✅ Kind post-deploy smoke — `./probe_smoke.sh` / `pytest -m live`.
3. ✅ CI on every PR/push — pytest gates merge; builds container image (no ACR).
4. ✅ LLM eval gate — mocked harness in CI + `@pytest.mark.live` httpx golden evals (port-forward).
5. ✅ Same image + base manifests on AKS via Terraform + Kustomize overlay (ACR pull via managed identity); smoke + live evals pass; destroyed when idle.

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
| 4 — Thin CI | **Done** | Mocked pytest + `docker build` ([green run](https://github.com/BrotherofOracleMan/AKS_AI_Observability_project/actions/runs/34544850875)) |
| 5 — Thin evals | **Done** | `pass_scorer` + CI (`not live`) + live httpx golden path |
| 6 — AKS + Terraform | **Done** | ACR + AKS via Terraform, Kustomize overlay, port-forward tests; [runbook.md](runbook.md) |
| Deferred | Later | [deferred-phases.md](deferred-phases.md) |
