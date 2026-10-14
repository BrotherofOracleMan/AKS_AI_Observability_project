# Architecture

How the pieces fit, why it's built this way, and how to explain it.

## The picture

```text
 client (curl / probe_smoke.sh / pytest)
        │  POST /v1/chat   (BASE_URL, usually localhost:8000 via port-forward)
        ▼
┌──────────────── Kubernetes (Kind or AKS) ────────────────┐
│  Service ai-on-kubernetes :8000   ← stable name          │
│        │                                                 │
│        ▼                                                 │
│  Pod: FastAPI proxy (our image)                          │
│    /health   → liveness + readiness probes               │
│    /v1/chat  → validate → call model → log → respond     │
│    env vars  ← Secret azure-openai (endpoint, key, ...)  │
└────────┼─────────────────────────────────────────────────┘
         │  HTTPS + API key
         ▼
 Azure OpenAI (ai_aks_resource_group)
   the model — hosted, scaled, and run on Microsoft's GPUs
```

**The model never runs in our cluster.** Azure OpenAI is a managed service. What we built is the **proxy layer** between clients and the model. The cluster only runs that lightweight proxy, so a 2-vCPU node is enough — no GPUs.

## Why a proxy in front of the model

| Benefit | Status |
|---------|--------|
| **Validation** — `ChatRequest` (pydantic) rejects bad bodies with 422 before anything reaches Azure | ✅ Built |
| **Enrichment / observability** — `request_id` + JSON log line with tokens per request | ✅ Built (latency currently logs ~0 ms — computed before the model call in `src/main.py`) |
| **Fast testing** — mocked pytest in CI (no Azure calls); live smoke + golden evals against the real model through the same endpoint | ✅ Built |
| **Key stays server-side** — only the proxy holds the Azure OpenAI key; clients send messages, never the model key | ✅ Built |
| **Clients decoupled from the model** — clients depend on our `/v1/chat` contract, not on Azure's API | ✅ Built |
| **Authentication + rate limiting** — per-client credentials, separate from the model key | ⏸️ Deferred — [deferred-phases.md](deferred-phases.md#public-exposure--api-auth) |

### Keys: proxy credential vs model key

- **Today:** clients need no credential at all — anyone who can reach `/v1/chat` can use the model through the proxy. That's why it's only reachable via port-forward.
- **With auth:** each client gets its **own** proxy key; the proxy alone holds the **model** key. Revoke one client without rotating the Azure key; rate-limit and log per client.
- **Later:** Workload Identity removes the model key entirely — the pod proves its identity to Azure ([deferred-phases.md](deferred-phases.md#workload-identity--secrets)).

### Swapping the model

The model is **config, not code**: `openai_client.py` sends `model=config.azure_openai_model` (`AZURE_OPENAI_MODEL` = the Azure OpenAI **deployment name**). The response shape is built by our code, so it doesn't change.

1. Deploy the new model in Azure OpenAI (new deployment name)
2. Update `AZURE_OPENAI_MODEL` in `secret.yaml` → `kubectl apply -f deployments/k8/secret.yaml`
3. `kubectl rollout restart deploy/ai-on-kubernetes`

Caveats: answers change even though the shape doesn't — **run the golden evals before switching**. `completion.model` in the response reveals which model answered. A different *provider* needs a code change, but only in `openai_client.py`.

## Same proxy, three places to run it

| Where the proxy runs | How | Model call goes to |
|----------------------|-----|--------------------|
| Laptop, no K8s | `uvicorn` or `docker run --env-file .env` | Azure OpenAI |
| Laptop, K8s | **Kind** — `kubectl apply -k deployments/k8` | Azure OpenAI |
| Cloud, K8s | **AKS** — [runbook.md](runbook.md) | Azure OpenAI |

### Kind vs AKS: what stays, what changes

**Stays the same (on purpose):** the image, the base manifests (`deployment.yaml`, `service.yaml`), the Secret pattern, the tests.

| | Kind (local) | AKS (cloud) |
|---|---|---|
| Cluster | Docker containers on the laptop, seconds to create | Azure-managed, created by **Terraform** (`infra/`) |
| Getting the image in | `kind load` — no registry | Push to **ACR**; nodes pull via the **AcrPull** role on the kubelet identity |
| Manifests | Base as-is: `ai-on-kubernetes:local`, `imagePullPolicy: Never` | **Kustomize overlay** `deployments/aks/` swaps image + pull policy |
| Cost | Free | ~$0.08/hr → **destroy after use** |
| Access | port-forward | port-forward (public LoadBalancer deferred until auth) |

## Kubernetes networking: names, not IPs

| Layer | Example (AKS run) | Stable? | Do we use it? |
|-------|-------------------|---------|---------------|
| Pod IP | `10.244.0.93` | ❌ changes on every restart/reschedule | Never — the Service tracks it |
| Service ClusterIP | `10.0.180.130` | ✅ for the Service's lifetime | Rarely |
| **Service name** | `ai-on-kubernetes` | ✅ | **Yes** — `port-forward svc/...`, in-cluster DNS |

- **Inside the cluster:** other pods call `http://ai-on-kubernetes:8000` (full name `ai-on-kubernetes.default.svc.cluster.local`). CoreDNS (`kube-dns`) resolves it to the ClusterIP; the Service routes to a healthy pod.
- **Why that matters:** pods restart, reschedule, roll out new versions, scale up — the Service name doesn't change, so clients don't notice. Readiness probes keep traffic off pods that aren't ready.
- **The Service finds pods by label:** `selector: app: ai-on-kubernetes` must match the pod template's labels, or the Service has no endpoints (`kubectl get endpoints ai-on-kubernetes`).
- **Outside the cluster** those names don't resolve — hence port-forward. For real external clients: LoadBalancer (external IP) or Ingress + a **public DNS name**. Pointing that DNS name at a new cluster is how you'd move clusters without users noticing.
- **Moving Kind → AKS** needed no app or manifest rewrites (containers + declarative manifests = portability), but the address did change — it only *looked* the same because port-forward maps both to `localhost:8000`.

## Config and secrets flow

```text
secret.yaml (stringData, gitignored)
   │  kubectl apply -f      → Secret azure-openai stored in etcd (namespace: default)
   ▼
deployment.yaml envFrom: secretRef: azure-openai
   │  kubelet on whichever node runs the pod fetches it
   ▼
container env vars  →  pydantic-settings Config()  →  app
```

- **Precedence in `Config()`:** init args → **environment variables** → `.env` file → field defaults. Locally the values come from `.env`; in the pod they come only from env vars — `.dockerignore` keeps `.env` out of the image.
- **All 5 fields are required** (`AZURE_OPENAI_ENDPOINT`, `_API_KEY`, `_MODEL`, `_API_VERSION`, `BASE_URL`). A missing one → `ValidationError` at import → `CrashLoopBackOff`.
- **`BASE_URL` is only used by tests** (`test_smoke.py`, `test_evals.py`) as the address to call. The app doesn't use it, but it must exist in the pod because the field is required — `http://localhost:8000` is a placeholder there.
- Field names match env vars **case-insensitively** (`azure_openai_api_key` ← `AZURE_OPENAI_API_KEY`). The `env="..."` arguments are pydantic v1 syntax that v2 ignores.
- **Works on any number of nodes:** a Secret is cluster state, not node state. Every replica on every node gets the same values.
- **Env vars are fixed at container start.** After changing the Secret: `kubectl rollout restart deploy/ai-on-kubernetes`.
- Secret must exist **before** the pod starts, else `CreateContainerConfigError`.
- Secrets are base64-encoded, not encrypted by default — fine for a lab; Workload Identity is the upgrade.

## Image vs container vs VM

- **Image** — the blueprint: app + dependencies + how to start it, built once (`Dockerfile`).
- **Container** — a **running instance** of an image: isolated process(es) on the host. Containers **share the host's kernel** (namespaces + cgroups) → lightweight, start in milliseconds.
- **VM** — virtualized hardware (hypervisor) running a **full OS with its own kernel** → heavier, but stronger isolation (separate kernel), can run a different OS, full OS control.
- **They stack:** the AKS node is a VM (`Standard_D2als_v7`); our containers run on it.

## Decisions vs quirks

Two different kinds of "why". **Decisions** we chose and can defend ("I chose X over Y because…"). **Quirks** the environment forced on us ("I hit this, found why, fixed it"). Understand the decisions; don't memorize the quirks — keep 2–3 as stories.

### Design decisions

| Decision | Instead of | Why | Trade-off / revisit when |
|----------|------------|-----|--------------------------|
| Proxy in front of a **managed model** (Azure OpenAI) | Self-hosting the model in K8s | No GPU nodes, quota, or model serving to run; cluster stays small and cheap | Self-host for data residency, custom/open models, or cost at high volume |
| **Proxy layer** owns validation, logging, the model key | Clients calling Azure OpenAI directly | One place for validation, observability, auth, model swaps; key never leaves the server | An extra hop to run and maintain |
| Model name is **config** (`AZURE_OPENAI_MODEL`) | Hardcoding it | Swap models with a Secret change + restart, no code change | Behavior changes silently → gate swaps with the golden evals |
| **Kustomize overlay** (`deployments/aks/`) | Two copies of the YAML | One base; overlay holds only the differences (image + pull policy) → no drift | One more tool/concept (`-k`) |
| **Kind first**, then AKS | Going straight to the cloud | Free, instant feedback loop; learn K8s without a meter running | Kind ≠ real cloud (no registry, no cloud identity) — AKS still needed to prove it |
| **Secret injected at runtime** (`envFrom`) | Baking config into the image | Same image everywhere; secrets stay out of git and the image | K8s Secrets are only base64 → Workload Identity next |
| **port-forward** for access | Public LoadBalancer | `/v1/chat` has no auth — a public IP lets anyone spend tokens | Add auth + rate limiting, then expose ([deferred-phases.md](deferred-phases.md#public-exposure--api-auth)) |
| **Mocked tests in CI**, live tests local | Live tests in CI | CI is fast, free, deterministic; no secrets in CI | Real-model regressions only caught when you run live evals |
| **Golden evals** with `contains` / `not_contains` | LLM-as-judge or Foundry evaluators | Cheap, deterministic, explainable gate | Only works for clear-answer prompts |
| **Terraform** + destroy after use | Portal clicks / leaving the cluster up | Reproducible create/destroy; ~$0.08/hr only while used | ~15 min to recreate; ACR name changes each time |
| **ACR + AcrPull** on the kubelet identity | ACR admin password / image pull secrets | No shared password in the cluster; Azure handles the token | Needs Owner/User Access Admin to create the role assignment |
| **Single small node** (`Standard_D2als_v7`, Free tier control plane) | Multi-node / Standard tier | Cheapest setup that works for a lab | No HA; upgrades briefly need a surge node |
| Image tags **`v1`, `v2`…** | Reusing `latest` | Obvious rollouts/rollbacks; `latest` changes pull-policy defaults | Must bump the tag (overlay `newTag`) per release |

### Quirks (environment-imposed)

| Quirk | Symptom | Cause | Fix |
|-------|---------|-------|-----|
| B-series VMs blocked | `NotAvailableForSubscription` / `InsufficientVCPUQuota` | Subscription limits; AKS also disallows B-series for system pools | `Standard_D2als_v7` (check with `az vm list-skus` / `list-usage`) |
| azurerm 4.x needs a subscription | `subscription ID could not be determined` | Provider no longer infers it | `export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)` |
| Apple Silicon builds arm64 | `exec format error` → `CrashLoopBackOff` | AKS node is x86 | `docker build --platform linux/amd64` |
| ACR name changes every recreate | `ImagePullBackOff` after a rebuild | Random suffix in Terraform | Re-tag + push; replace `<REGISTRY>` in the overlay locally (committed version keeps the placeholder) |
| `BASE_URL` required in the pod | `ValidationError` → `CrashLoopBackOff` | Required pydantic field; app never uses it (tests do); no `.env` in the image | Add it to the Secret (or give it a default) |
| `kubectl apply -f <folder>` fails | `kind not set` / `name not set` | `-f` treats `kustomization.yaml` as a K8s object | `-k` for kustomize folders |
| `kubectl logs app=...` fails | `NotFound` pod named `app=...` | Missing `-l`, so it's read as a pod name | `-l app=ai-on-kubernetes` |
| `get deploy,svc -l app=...` shows only the pod | Looks like nothing deployed | Label is on the pod template, not the Deployment/Service metadata | Drop `-l` for those |
| port-forward hits the "wrong" cluster | Tests pass but not where you think | port-forward stays bound to the context it started in | Restart it with `--context`; tail that cluster's logs |
| Secret edit has no effect | Old values still in the pod | Env vars are fixed at container start | `kubectl rollout restart deploy/ai-on-kubernetes` |
| `IMDSUnreachable` at boot | Warning event on the node | Metadata service not ready yet when the node starts | Ignore if it stops and images pull |
| `destroy` is slow | 5–15 min of `Still destroying...` | AKS deletes node, LB, IP, VNet, disks, `MC_*` group | Wait; never Ctrl+C; re-run if it fails |
| Latency logs ~0 ms | `latency_ms` always tiny | Computed before the model call in `src/main.py` | Move it after `chat(request)` (open bug) |

### Story worth telling: the `BASE_URL` crash

> "Before deploying to AKS I traced how config reaches the app and found a crash waiting to happen: the config class required `BASE_URL`, which only the tests use. Locally it came from `.env`, but `.dockerignore` keeps `.env` out of the image, so in the cluster the Secret is the only source — and it didn't have that key. Without it the pod would crash-loop with a pydantic `ValidationError`. I added it to the Secret, and the pod came up clean first time. It taught me how config actually flows: Secret → `envFrom` → env vars → pydantic, and that env vars are fixed at container start."

Tell it as it happened — you caught it before deploying; it didn't crash on AKS.

## Talking about it

### 30-second architecture

> "Clients call a small FastAPI proxy running in Kubernetes. The proxy calls Azure OpenAI, where Microsoft hosts and scales the model. My cluster only runs the lightweight proxy. That layer is where I control things — validation, request IDs and token logging, the API key stays server-side, and I test against it: mocked in CI and live evals against the real model."

### Image vs container vs VM (~45 s)

> "An image is the blueprint — my app, its dependencies, and how to start it. A container is a running instance of that image: an isolated process on the host. Containers share the host's kernel, so they're lightweight and start in milliseconds. A VM virtualizes hardware and runs its own full OS, so it's heavier but gives stronger isolation and can run a different OS. In practice you use both — my containers ran on an Azure VM node in AKS."

### Local vs cloud

> "I built one container and ran it unchanged on my laptop and in Azure. The cloud infrastructure is Terraform, so I create it and tear it down on demand to control cost. The only manifest difference is a Kustomize overlay that points at the registry image."

Recruiter: the one-liner is enough. Technical interviewer: walk the Kind vs AKS table and expect "why" follow-ups.

### Demo (run the live part on Kind — free, instant, no surprises)

1. **Architecture** (30 s) — the picture above
2. **Files** — `Dockerfile`, `deployments/k8/`, `deployments/aks/` overlay, `infra/`
3. **Live** —
   ```bash
   kubectl config use-context kind-kind
   kubectl apply -f deployments/k8/secret.yaml
   kubectl apply -k deployments/k8
   kubectl port-forward svc/ai-on-kubernetes 8000:8000
   curl -s http://localhost:8000/health
   ./probe_smoke.sh
   BASE_URL=http://localhost:8000 uv run pytest tests/test_evals.py -m live -v
   ```
4. **Inspect** — `kubectl get pods -l app=ai-on-kubernetes`, `kubectl logs deploy/ai-on-kubernetes --tail=20`
5. **CI** — GitHub Actions: mocked pytest + eval harness + image build
6. **Cloud + cost** — "Same image and base manifests ran on AKS via Terraform; ~$0.08/hr, destroyed after use; [runbook.md](runbook.md) rebuilds it in ~15 min."

### Likely follow-ups

| Question | Answer |
|----------|--------|
| Why not run the model in K8s? | GPU nodes (cost, quota) + model serving (vLLM etc.). Managed service offloads that. Self-host for data residency, custom/open models, or cost at high volume. |
| What does the proxy add? | Validation, logging, key stays server-side, one place for auth/rate limits/model swaps, testable contract. |
| Where does the key live? | K8s Secret → env var in the pod. Next step: Workload Identity (no key). |
| Why Kustomize, not two copies of YAML? | One base; the overlay holds only the differences (image + pull policy). No drift between environments. |
| Why is the Secret applied separately? | It's gitignored (holds the key), so it's not in the kustomization. |
| Why does AKS need a registry and Kind doesn't? | Kind nodes are local containers that can be loaded directly; AKS nodes are Azure VMs that pull images over the network. |
| Why no public LoadBalancer? | `/v1/chat` has no auth yet — a public IP would let anyone spend tokens. |
| How would you swap models? | Config change (`AZURE_OPENAI_MODEL`) + rollout restart, gated by the golden evals. |
