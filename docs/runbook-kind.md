# Runbook — Kind create → deploy → test → tear down

Copy-paste path for running the app on a local Kind cluster. Same image, same base manifests, same tests as AKS ([runbook.md](runbook.md)) — but free, and no Terraform.

## How Kind differs from AKS

| | Kind | AKS |
|---|---|---|
| Cluster | Docker container on your Mac (`kind-control-plane`) | Azure VM node, created by Terraform |
| Manifests | `kubectl apply -k deployments/k8` (base only) | `-k deployments/aks` (base + overlay) |
| Namespace | `default` — no `-n` needed | `ai-proxy-ns` |
| Getting the image in | `kind load docker-image` — no registry | Push to ACR |
| Image arch | Your Mac's (arm64 on Apple Silicon) — no `--platform` | `linux/amd64` |
| Azure OpenAI auth | **API key** — Kind has no Workload Identity webhook or managed identity, and your `az login` lives on the Mac, not in the pod | Workload Identity token, no key |
| Cost | $0 | ~$0.08/hr |

## Prereqs

- Docker Desktop running, `kind`, `kubectl`, `uv`
- `deployments/k8/secret.yaml` with **all 5 keys**, including `AZURE_OPENAI_API_KEY`:

  ```bash
  cp deployments/k8/secret.example.yaml deployments/k8/secret.yaml   # gitignored
  # fill in from your .env
  ```

## 1. Create the cluster (~1 min, once)

```bash
kind get clusters                 # "kind" → already exists, skip to step 2
kind create cluster               # cluster "kind", context "kind-kind"
```

The cluster survives Docker Desktop restarts (the `kind-control-plane` container restarts with it). If `kubectl` says `connection refused` on `127.0.0.1:<port>`, Docker isn't running.

## 2. Connect kubectl

```bash
kubectl config use-context kind-kind
kubectl config current-context    # kind-kind — NOT ai-on-kubernetes-aks
kubectl get nodes                 # kind-control-plane, Ready
```

## 3. Build and load the image

```bash
docker build -t ai-on-kubernetes:local .
kind load docker-image ai-on-kubernetes:local
docker exec kind-control-plane crictl images | grep ai-on-kubernetes   # check it's on the node
```

- The Deployment uses `image: ai-on-kubernetes:local` with `imagePullPolicy: Never` — the node never pulls, it only uses what `kind load` copied in. Forget the load → `ErrImageNeverPull`.
- The Dockerfile installs from `requirements.txt`. After any `uv add`, re-export before building: `uv export --no-dev --no-emit-project -o requirements.txt`.

## 4. Deploy

```bash
kubectl apply -f deployments/k8/secret.yaml   # secret first (with the key)
kubectl apply -k deployments/k8               # -k, not -f
kubectl rollout status deploy/ai-on-kubernetes
kubectl get pods -l app=ai-on-kubernetes      # 1/1 Running
```

**Redeploying after a code change:** the tag stays `:local`, so the Deployment spec doesn't change and `apply` alone won't replace the pod. After step 3, restart it:

```bash
kubectl rollout restart deploy/ai-on-kubernetes
kubectl rollout status deploy/ai-on-kubernetes
```

Same after editing `secret.yaml` — env vars are read only at container start.

## 5. Test

```bash
kubectl port-forward svc/ai-on-kubernetes 8000:8000    # leave running

# second terminal:
curl -s http://localhost:8000/health
./probe_smoke.sh
BASE_URL=http://localhost:8000 uv run pytest tests/test_smoke.py tests/test_evals.py -m live -v
```

Live tests call real Azure OpenAI and cost tokens. Logs should show `POST …/chat/completions "HTTP/1.1 200 OK"` and a non-zero `latency_ms`:

```bash
kubectl logs deploy/ai-on-kubernetes -f | grep -v /health
```

## 6. Tear down

Pick one:

```bash
# Remove the app, keep the cluster (fast to redeploy)
kubectl delete -k deployments/k8
kubectl delete secret azure-openai

# Or delete the whole cluster (also removes the kind-kind context)
kind delete cluster
```

Kind costs nothing, so leaving it running is fine — it only uses Docker Desktop's memory.

## Debugging

| Symptom | Fix |
|---------|-----|
| `connection refused` on `127.0.0.1:<port>` from kubectl | Docker Desktop not running, or the cluster was deleted → step 1 |
| `ErrImageNeverPull` | Image not loaded into Kind → step 3 (`kind load`) |
| Pod still runs old code | Same `:local` tag → `kubectl rollout restart deploy/ai-on-kubernetes` |
| `ModuleNotFoundError` on start | `requirements.txt` not re-exported after `uv add` → step 3 |
| `CreateContainerConfigError` | Secret not applied → step 4 |
| `CrashLoopBackOff` + pydantic `ValidationError` | Secret missing a required key → fix `secret.yaml`, re-apply, `rollout restart` |
| `DefaultAzureCredential failed to retrieve a token` | `AZURE_OPENAI_API_KEY` missing from the secret — Kind can't get a token, it needs the key |
| `kind not set` / `name not set` | Used `-f` on a kustomize folder → use `-k` |
| `curl: connection refused` on `localhost:8000` | port-forward not running, or it died after a pod restart → start it again |
| Traffic going to the wrong cluster | port-forward stays bound to the context it was started with → check `current-context`, restart the forward |

Manifest walkthrough and learning notes: [deployments/k8/README.md](../deployments/k8/README.md). kubectl reference (contexts, `-f` vs `-k`, labels, logs vs events): [runbook.md](runbook.md#kubectl-reference).
