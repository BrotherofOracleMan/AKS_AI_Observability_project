# Deferred phases

Optional work **after** the sequential core path (Phases **0–6**, done).

Back to main roadmap: [project-roadmap.md](project-roadmap.md).

| Topic | Revisit if… |
|-------|-------------|
| **Workload Identity** | Security/compliance QA or Azure-heavy platform roles |
| **Thin RAG** | AI product QA; grounded-answer test scenarios |
| **GitOps** | Platform/SRE-leaning SDET or infra QA |
| **Optional Go** | Custom cluster smoke tool beyond pytest + shell |
| **Public exposure + API auth** | You need a shareable demo URL instead of port-forward |

---

## Workload Identity & secrets

**Learn:** keyless pod → Azure OpenAI; tighten secret handling.

**Why:** Long-lived API keys in Secrets are a weak demo story. Workload Identity is what production AKS + Azure AI setups aim for.

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

## Public exposure + API auth

**Learn:** protect an LLM proxy before giving it a public IP.

**Why:** Deferred from Phase 6. `/v1/chat` has no auth, so a public LoadBalancer lets anyone who finds the IP spend Azure OpenAI tokens. Phase 6 uses `kubectl port-forward` instead.

- [ ] Add API auth to `/v1/chat` (e.g. API key header checked in the app; key from a K8s Secret); keep `/health` open for probes
- [ ] Add basic rate limiting
- [ ] Tests: missing/wrong key → 401; valid key → 200
- [ ] Expose via a LoadBalancer patch in `deployments/aks/kustomization.yaml` (JSON6902 `op: add`, `path: /spec/type`, `value: LoadBalancer` on the Service) or Ingress (App Routing add-on)
- [ ] Remove the public Service when the demo is over (public IP charge)

**Done when:** the public endpoint rejects unauthenticated requests, and smoke/evals pass against it with the key.

| Reading | Why | Status |
|---------|-----|--------|
| [AKS App Routing (managed NGINX Ingress)](https://learn.microsoft.com/azure/aks/app-routing) | The "real" way to expose HTTP on AKS | New |
| [FastAPI security](https://fastapi.tiangolo.com/tutorial/security/) | API key / bearer auth in the app | New |

---

## Thin RAG

**Learn:** retrieve a little context; keep the proxy thin.

- [ ] Tiny corpus (markdown/files) + simple retrieval (embeddings or keyword OK for lab)
- [ ] Inject retrieved snippets into the chat request path
- [ ] Test: grounded answer when context present; safe fallback when not
- [ ] Document limits (not a full vector DB platform)

**Done when:** one demo query clearly uses retrieved context; tests cover the path.

---

## GitOps

**Learn:** desired state in git; cluster reconciles (Argo CD or Flux).

- [ ] Install Argo CD or Flux on lab AKS (destroy with cluster)
- [ ] Point it at `deployments/k8/` (or a git path)
- [ ] Show: merge → sync → pod rolls; document in runbook

**Done when:** a manifest change ships via git sync, not only `kubectl apply` by hand.

---

## Optional — Go + client-go

**Why:** Many platform tools use Go + client-go. A tiny companion CLI shows you understand the control plane API.

- [ ] Small module under `cmd/k8s-inspect/`
- [ ] Print pod phase, ready condition, restart count, and image tag
- [ ] Optional: exit non-zero if no ready replicas (CI smoke helper)

**Interview one-liner:** “The app is Python on K8s; I added a small Go utility with client-go that lists proxy pods and readiness — same API kubectl uses, but automatable.”
