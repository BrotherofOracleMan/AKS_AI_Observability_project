# Deferred phases

Optional work **after** the core path (Phases 0–5) and Phase 8 (evals). Lower priority for [SDET testing & automation track](project-roadmap.md#sdet-upskill-track--testing--automation) — revisit for platform, backend, or AI-product portfolio paths.

Back to main roadmap: [project-roadmap.md](project-roadmap.md).

| Phase | Revisit if… |
|-------|-------------|
| **6 — Workload Identity** | Security/compliance QA or Azure-heavy platform roles |
| **7 — Thin RAG** | AI product QA; grounded-answer test scenarios |
| **9 — GitOps** | Platform/SRE-leaning SDET or infra QA |
| **Optional — Go** | Custom cluster smoke tool beyond pytest + shell |

---

## Phase 6 — Workload Identity & secrets

**SDET Tier 3** — security/infra depth; skip unless role needs it.

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

## Phase 7 — Thin RAG

**SDET Tier 3** — feature work; skip unless targeting AI product QA.

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

## Phase 9 — GitOps

**SDET Tier 3** — deployment sync; weak signal for pure test/automation roles.

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

## Optional — Go + client-go (Kubernetes API)

**SDET Tier 3** — only if framed as test tooling (readiness checker, smoke Job). pytest + curl + Actions is enough for most SDET goals.

**When:** after the core path (Phases 0–5) and ideally after you’ve run on Kind **and** AKS. **Not blocking** anything — Python proxy + manifests stay the main artifact.

**Learn:** talk to the Kubernetes API from code (not only `kubectl`); in-cluster vs kubeconfig auth; typed clients for core resources.

**Why:** Many platform tools (kubectl, controllers, operators) are Go + client-go. A tiny companion CLI shows you understand the **control plane API**, not just YAML apply — useful if interviews drift toward “how would you automate pod health checks?”

### Scope (keep thin)

- [ ] `cmd/k8s-inspect/` — single binary, `go mod init` at repo root or under `cmd/`
- [ ] Load config: `KUBECONFIG` locally; `rest.InClusterConfig()` when run as a Pod/Job later (optional)
- [ ] List pods for the proxy Deployment (label selector `app=ai-on-kubernetes` or your manifest labels)
- [ ] Print pod phase, ready condition, restart count, and image tag
- [ ] Optional: `watch` mode or exit non-zero if no ready replicas (CI smoke against Kind or AKS)
- [ ] `go test` with envtest or a fake clientset for one happy path (no live cluster required in CI)

**Done when:** `go run ./cmd/k8s-inspect` against Kind or AKS prints the proxy pods; you can explain client-go vs `kubectl` and when you’d use each.

### Commands (sketch)

```bash
# After Kind/AKS + manifests from Phase 3–4
go run ./cmd/k8s-inspect --namespace default --selector app=ai-on-kubernetes

# Same binary inside the cluster (optional later)
kubectl apply -f deploy/k8s/k8s-inspect-job.yaml
kubectl logs job/k8s-inspect
```

### Pitfalls

- Don’t rebuild the proxy in Go — keep FastAPI as the workload; Go is **ops/inspection** only
- Match label selectors to your real `deploy/k8s/` manifests
- Rate-limit `watch` loops in demos; prefer one-shot list for interviews

| Reading | Why | Status |
|---------|-----|--------|
| [client-go — getting started](https://github.com/kubernetes/client-go) | Official Go client; module layout | New |
| [Accessing the cluster from a pod](https://kubernetes.io/docs/tasks/access-application-cluster/access-cluster/) | ServiceAccount + in-cluster config | New |
| [Kubernetes API concepts](https://kubernetes.io/docs/reference/kubernetes-api/) | Resources, list/watch, field selectors | New |
| [client-go examples](https://github.com/kubernetes/client-go/tree/master/examples) | List pods, informers (skim informers only) | New |
| [Go modules](https://go.dev/doc/modules/managing-dependencies) | `go.mod` / pinning client-go to cluster minor version | Known |

**Interview one-liner:** “The app is Python on K8s; I added a small Go utility with client-go that lists proxy pods and readiness — same API kubectl uses, but automatable in CI or a Job.”
