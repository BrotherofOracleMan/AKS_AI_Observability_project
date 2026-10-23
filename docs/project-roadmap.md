# Project Roadmap: Azure AI on Kubernetes

Learning-focused guide. Hero skills: **Azure + AI + Kubernetes + testing**. Observability stays thin: structured logs, `kubectl`, and Application Insights (Phase 10) — no Prometheus/Grafana stack.

**One sequence — do not skip ahead or jump around.** Finish each phase’s “Done when” before the next.

```text
0 Skeleton → 1 Azure OpenAI → 2 Docker → 3 Kind → 4 CI → 5 Evals → 6 AKS
→ 7 Workload Identity → 8 API auth + resilience → 9 Kind in CI
→ 10 Observability → 11 Thin RAG + LLM-as-judge
```

**Status:** Phases **0–7 done**; next: [Phase 8](#phase-8--api-auth--resilience). Architecture + how to explain it: [architecture.md](architecture.md). AKS commands: [runbook.md](runbook.md).

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

**Goals:** learn Azure + AI hands-on, with testing at every layer. API proxy → Docker → Kind + smoke → CI merge gates → eval gate → AKS with Terraform (same manifests) → keyless identity → authenticated, failure-tolerant API → deploy-and-test on Kind in CI → Azure observability → thin RAG with model-graded evals.

**Non-goals:** Prometheus/Grafana stacks, GPU pools, service mesh, fine-tuning, multi-cluster, GitOps, Go tooling — see [Out of scope](#out-of-scope--maybe-later).

---

## Suggested repo layout

```
azure_ai_on_kubernetes/
  README.md
  docs/project-roadmap.md   # this file
  docs/architecture.md      # design, K8s concepts, how to explain it
  docs/runbook.md           # AKS create → deploy → test → destroy
  docs/runbook-kind.md      # Kind create → deploy → test → tear down
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
| Request / latency / tokens | Structured logs from the proxy → Application Insights (Phase 10) |
| Pod health | `kubectl get/describe/logs` |
| Provider errors | Log status; retries + clear error codes (Phase 8); keep quotas low |

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

Verified green run: [Actions #34544850875](https://github.com/BrotherofOracleMan/azure_ai_on_kubernetes/actions/runs/34544850875) (`test / test` + `build`).

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
- [x] Port-forward for demo (public LoadBalancer waits for API auth — [Phase 8](#phase-8--public-exposure--api-auth))
- [x] `docs/runbook.md` create/destroy + cost notes
- [x] Reuse `./probe_smoke.sh` / live tests against the AKS tunnel

**Done when:** chat works on AKS; `terraform destroy` practiced. ✅

| Reading | Status |
|---------|--------|
| [ACR intro](https://learn.microsoft.com/azure/container-registry/container-registry-intro) | Known |
| [AKS + Terraform](https://learn.microsoft.com/azure/aks/learn/quick-kubernetes-deploy-terraform) | New |
| [ACR + AKS auth](https://learn.microsoft.com/azure/aks/cluster-container-registry-integration) | New |
| [AKS cost best practices](https://learn.microsoft.com/azure/aks/best-practices-cost) | New |

Keyless identity → [Phase 7](#phase-7--workload-identity--secrets).

---

### Phase 7 — Workload Identity & secrets

**Learn:** keyless pod → Azure OpenAI; tighten secret handling.

**Why:** Long-lived API keys in Secrets are a weak demo story. Workload Identity is what production AKS + Azure AI setups aim for.

- [x] Terraform: `workload_identity_enabled = true` + `oidc_issuer_enabled = true` on the AKS cluster (the OIDC issuer already came up enabled by AKS default; workload identity was off)
- [x] User-assigned managed identity with the **Cognitive Services OpenAI User** role on the Azure OpenAI resource (`ai_aks_resource_group` isn't Terraform-managed → reference it with a `data` block), plus a federated credential for the pod's ServiceAccount — applied and verified on AKS (webhook running, OIDC issuer on), then destroyed
- [x] Dedicated ServiceAccount `ai-proxy` (base) + `azure.workload.identity/use: "true"` pod label and `client-id` annotation (AKS overlay, `<CLIENT_ID>` placeholder) — deployed and verified on AKS: webhook injects `AZURE_CLIENT_ID`/`AZURE_TENANT_ID`/`AZURE_FEDERATED_TOKEN_FILE`/`AZURE_AUTHORITY_HOST`
- [x] Code: `openai_client.py` passes `api_key=` → use `azure_ad_token_provider` (`azure-identity` `DefaultAzureCredential`) when no key is set
- [x] Config: make `AZURE_OPENAI_API_KEY` optional in `src/config.py` — it's required today, so removing it from the Secret crash-loops the pod (same failure as the `BASE_URL` story). **Kind keeps using the key** (its OIDC issuer isn't reachable by Entra), so support both. Verified 2026-10-22: AKS secret without the key → `/v1/chat` 200, live smoke tests pass
- Egress lock-down → moved to [Out of scope](#out-of-scope--maybe-later)
- [x] Update `docs/runbook.md` with the identity story

**Done when:** chat on AKS works **without** an API key in the pod Secret; Kind still works with the key; you can explain the identity chain in an interview.

| Reading | Why | Status |
|---------|-----|--------|
| [AKS workload identity](https://learn.microsoft.com/azure/aks/workload-identity-overview) | Pod → Entra identity | Known MI idea; **New** on AKS |
| [OpenAI + Managed Identity](https://learn.microsoft.com/azure/foundry-classic/openai/how-to/managed-identity) | Keyless calls to the model | New |

---

### Phase 8 — API auth + resilience

**Learn:** protect an LLM proxy, and test how it behaves when Azure OpenAI fails.

**Why:** `/v1/chat` has no auth, so a public endpoint would let anyone spend tokens. And today any Azure error (429 quota, 500, timeout, content-filter block) surfaces as an unhandled 500 — the most common real-world LLM failures are untested.

- [ ] API auth on `/v1/chat`: key header checked in the app; key from a K8s Secret (Kind and AKS); `/health` stays open for probes
- [ ] Basic rate limiting (in-memory is per pod — fine for 1 replica; note the limit)
- [ ] Retries with backoff on Azure `429`/`5xx` (the OpenAI SDK has `max_retries` — learn what it does before adding your own)
- [ ] Map Azure failures to clear proxy responses: quota → `429`, timeout → `504`, content filter → `400` with a reason, other → `502`
- [ ] Fault-injection tests (mocked, run in CI): Azure returns 429 / 500 / timeout / content-filter → assert retries and status codes
- [ ] Auth tests: missing/wrong key → 401; valid key → 200; live smoke/evals send the key header
- [ ] Optional: public LoadBalancer patch in the AKS overlay (`op: add`, `path: /spec/type`, `value: LoadBalancer`) — remove it after the demo (public IP charge)

**Done when:** unauthenticated requests get 401, each injected Azure failure has a test with the expected status, and smoke/evals pass with the key.

| Reading | Why | Status |
|---------|-----|--------|
| [Azure OpenAI quotas and limits](https://learn.microsoft.com/azure/ai-services/openai/quotas-limits) | What TPM/RPM limits mean, where 429s come from | New |
| [Azure OpenAI content filtering](https://learn.microsoft.com/azure/ai-services/openai/concepts/content-filter) | What a blocked request looks like | New |
| [FastAPI security](https://fastapi.tiangolo.com/tutorial/security/) | API key / bearer auth in the app | New |

---

### Phase 9 — Kind in CI

**Learn:** test the deployed system on every push, not just the code.

**Why:** CI runs pytest and `docker build`, but never deploys the image. Manifest mistakes (wrong label, missing env, bad probe) only show up when you deploy by hand. This reuses [runbook-kind.md](runbook-kind.md) as a pipeline.

- [ ] Mock mode for the app: an env flag that returns `fake_chat_completion()` instead of calling Azure (already in `src/openai_client.py`) — CI has no Azure credentials
- [ ] GitHub Actions job: create a Kind cluster (`helm/kind-action`), build + `kind load` the image, apply `deployments/k8` with a CI secret, `kubectl rollout status --timeout`
- [ ] Run `tests/test_smoke.py` against the pod via port-forward
- [ ] On failure, dump `kubectl describe` / `logs` / events into the job output
- [ ] Image build waits for this job (same gate as today's mock tests)

**Done when:** a broken manifest (e.g. wrong Service selector) fails CI with a readable reason.

| Reading | Why | Status |
|---------|-----|--------|
| [kind in CI](https://kind.sigs.k8s.io/docs/user/quick-start/) | Cluster in a GitHub runner | Known Kind; **New** in CI |

---

### Phase 10 — Observability (Application Insights)

**Learn:** see what each LLM request costs and where latency comes from — in Azure, not just `kubectl logs`.

**Why:** The structured logs already have `request_id`, `latency_ms`, `tokens`. Sending them to Azure Monitor makes them queryable and chartable. Also verifies Phase 8: injected failures should show up as errors.

- [ ] Terraform: Log Analytics workspace + workspace-based Application Insights; connection string → Secret
- [ ] App: `azure-monitor-opentelemetry` (`configure_azure_monitor()`) — auto-traces FastAPI requests and the outbound Azure OpenAI call
- [ ] Custom dimensions on the chat span/log: tokens (prompt/completion), model, status
- [ ] KQL queries: p50/p95 latency, tokens per request, estimated cost per day, error rate
- [ ] A small workbook or dashboard with those queries
- [ ] Kind: also works (connection string in the Kind secret); CI mock mode leaves it off

**Done when:** you can answer "what did yesterday's requests cost and what was p95 latency?" from Azure.

| Reading | Why | Status |
|---------|-----|--------|
| [Azure Monitor OpenTelemetry for Python](https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-enable?tabs=python) | One-call setup | New |
| [KQL quick reference](https://learn.microsoft.com/kusto/query/kql-quick-reference) | Query logs/traces | New |

---

### Phase 11 — Thin RAG + LLM-as-judge

**Learn:** retrieve a little context; grade answers that can't be string-matched.

**Why:** RAG is the most common real use of LLMs. Its answers vary in wording, so `must_contain` stops working — model-graded evals are how teams test this.

- [ ] Tiny corpus (markdown/files) in the image or a ConfigMap
- [ ] Simple retrieval — start with keyword (no new Azure resources); embeddings need an embeddings deployment in Azure OpenAI (quota + cost)
- [ ] Inject retrieved snippets into the chat request path
- [ ] LLM-as-judge scorer: a second model call grades groundedness/relevance against a rubric → score 1–5
- [ ] Eval gate: pass rate over a golden set ≥ threshold (e.g. 90%), not every case must pass; print a per-case report
- [ ] Tests: grounded answer when context present; safe fallback when not (mocked + live)
- [ ] Document limits (not a full vector DB platform; judge models have their own bias)

**Done when:** one demo query clearly uses retrieved context, and a live eval run reports a pass rate that gates on a threshold.

| Reading | Why | Status |
|---------|-----|--------|
| [RAG in Azure AI Search](https://learn.microsoft.com/azure/search/retrieval-augmented-generation-overview) | Concepts + the "real" Azure path | New |
| [Eval approach for generative AI](https://learn.microsoft.com/azure/ai-foundry/concepts/evaluation-approach-gen-ai) | Groundedness/relevance metrics | Skimmed in Phase 5 |

---

## Out of scope / maybe later

Cut to keep the project on Azure + AI + testing. Notes kept so the thinking isn't lost.

| Idea | Why cut | Notes if picked up |
|---|---|---|
| **Egress lock-down** (was Phase 7) | Networking-heavy; the useful version needs paid add-ons | Set `network_profile.network_policy` (empty on the last cluster — Azure CNI overlay ignores NetworkPolicy objects), deny all egress except DNS + 443. Allowing only the OpenAI hostname needs Cilium FQDN policies or Azure Firewall |
| **Go + client-go** (was Phase 10) | Not Azure, AI or testing; `kubectl rollout status` covers the CI readiness check | `cmd/k8s-inspect/`: pod phase, ready condition, restarts, image tag; exit non-zero if no ready replicas |
| **GitOps** (was Phase 11) | Large platform effort; tight on a 2-vCPU node | Flux (AKS extension) on the `deployments/aks/` overlay; needs a stable ACR name, a committed ConfigMap for non-secret config, and Sealed Secrets or Key Vault CSI for the Phase 8 proxy key |
| **Load testing** (k6 / Locust) | Stretch | p50/p95 under concurrency; find where Azure starts returning 429 — pairs with Phases 8 and 10 |
| **Contract testing** (Schemathesis) | Stretch | Fuzz `/v1/chat` from FastAPI's OpenAPI spec |

---

## Pace (same order as phases)

| When | Phase |
|------|--------|
| Done | 0–7 |
| Next | 8 → 9 → 10 → 11 |

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

1. ✅ Automated API tests — mocked Azure OpenAI (no token spend with `pytest -m "not live"`).
2. ✅ Kind post-deploy smoke — `./probe_smoke.sh` / `pytest -m live`.
3. ✅ CI on every push — mocked pytest; a failure blocks the container image build (no ACR).
4. ✅ LLM eval gate — mocked harness in CI + `@pytest.mark.live` httpx golden evals (port-forward).
5. ✅ Same image + base manifests on AKS via Terraform + Kustomize overlay (ACR pull via managed identity); smoke + live evals pass; destroyed when idle.
6. ✅ Keyless Azure OpenAI on AKS — Entra Workload Identity (federated credential, least-privilege OpenAI User role); no API key in the cluster.

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
| 4 — Thin CI | **Done** | Mocked pytest + `docker build` ([green run](https://github.com/BrotherofOracleMan/azure_ai_on_kubernetes/actions/runs/34544850875)) |
| 5 — Thin evals | **Done** | `pass_scorer` + CI (`not live`) + live httpx golden path |
| 6 — AKS + Terraform | **Done** | ACR + AKS via Terraform, Kustomize overlay, port-forward tests; [runbook.md](runbook.md) |
| 7 — Workload Identity | **Done** | Keyless AKS → Azure OpenAI; Kind keeps the key; [runbook.md](runbook.md) |
| 8 — API auth + resilience | Not started | Key header, rate limit, retries, fault-injection tests |
| 9 — Kind in CI | Not started | Deploy + smoke on every push, mock mode |
| 10 — Observability | Not started | App Insights, KQL, cost per request |
| 11 — Thin RAG + LLM-as-judge | Not started | Keyword retrieval first; pass-rate gate |
