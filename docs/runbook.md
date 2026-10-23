# Runbook — AKS create → deploy → test → destroy

Copy-paste path for running the app on AKS. Same image, same base manifests, same tests as Kind ([runbook-kind.md](runbook-kind.md)).

## Cost

| Item | Approx. cost (eastus) |
|------|------------------------|
| 1 × `Standard_D2als_v7` node | ~$0.08/hr (~$59/mo if never destroyed) |
| AKS control plane (Free tier) | $0 |
| ACR Basic | ~$0.17/day |
| Load balancer, outbound IP, OS disk | small; created by AKS automatically |

**Destroy when done.** Billing stops once `terraform destroy` finishes.

## Prereqs

- `az login` (right subscription: `az account show -o table`)
- Docker Desktop running, Terraform ≥ 1.1, kubectl
- `deployments/k8/secret.yaml` exists with `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_MODEL`, `AZURE_OPENAI_API_VERSION`, `BASE_URL` (all required by `src/config.py`). `AZURE_OPENAI_API_KEY` is optional: Kind needs it, AKS leaves it out (step 5) so the pod uses Workload Identity
- Everything on AKS lives in namespace `ai-proxy-ns` — every `kubectl` command needs `-n ai-proxy-ns` (or run `kubectl config set-context --current --namespace=ai-proxy-ns` once after step 2)

## 1. Create infra (~5–10 min)

Creates: resource group, ACR (random name suffix), AKS (1 node, OIDC issuer + workload identity on), AcrPull role for the nodes, managed identity `ai_on_aks` with **Cognitive Services OpenAI User** on `ai-aks-learning`, and its federated credential for `system:serviceaccount:ai-proxy-ns:ai-proxy`.

```bash
cd infra
export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
terraform init
terraform plan -out tfplan        # expect: 8 to add, 0 to change, 0 to destroy
terraform apply tfplan
```

## 2. Connect kubectl

```bash
az aks get-credentials \
  -g $(terraform output -raw aks_resource_group_name) \
  -n $(terraform output -raw aks_name) --overwrite-existing
kubectl config current-context    # ai-on-kubernetes-aks — NOT kind-kind
kubectl get nodes                 # 1 node, Ready
```

## 3. Push the image to ACR

The ACR name changes on every create, so re-tag and push each time.

```bash
ACR=$(terraform output -raw acr_name)
LOGIN=$(terraform output -raw acr_login_server)
cd ..
az acr login --name $ACR

# Re-tag the existing amd64 v3 image (still tagged with an old ACR name locally):
docker tag $(docker images -q --filter "reference=*/ai-on-kubernetes:v3" | head -1) $LOGIN/ai-on-kubernetes:v3
# Or rebuild (amd64 is required — the node is x86):
# docker build --platform linux/amd64 -t $LOGIN/ai-on-kubernetes:v3 .

docker push $LOGIN/ai-on-kubernetes:v3
```

The Dockerfile installs from `requirements.txt`, not `pyproject.toml`. After any `uv add`, re-export before building, or the image silently misses the package (`ModuleNotFoundError` on start):

```bash
uv export --no-dev --no-emit-project -o requirements.txt
```

## 4. Fill the AKS overlay placeholders

The committed overlay has two placeholders that change on every recreate — fill them locally, **don't commit the real values**:

| Placeholder | Replace with |
|---|---|
| `newName: <REGISTRY>/ai-on-kubernetes` | `$LOGIN` |
| `azure.workload.identity/client-id: <CLIENT_ID>` | `terraform -chdir=infra output -raw workload_identity_client_id` |

```bash
kubectl kustomize deployments/aks | grep -E 'image:|imagePullPolicy:|client-id|workload.identity/use|namespace:'
# expect: image: <LOGIN>/ai-on-kubernetes:v3
#         imagePullPolicy: IfNotPresent
#         azure.workload.identity/client-id: <real GUID>
#         azure.workload.identity/use: "true"
#         namespace: ai-proxy-ns   (×3)
```

Revert both before committing: `git checkout -- deployments/aks/kustomization.yaml` (only if you made no other edits there).

## 5. Deploy

```bash
kubectl config current-context                # must be the AKS context
kubectl apply -k deployments/aks              # -k, not -f; creates ai-proxy-ns + SA + Deployment + Service
grep -v AZURE_OPENAI_API_KEY deployments/k8/secret.yaml | kubectl apply -n ai-proxy-ns -f -   # keyless secret
kubectl -n ai-proxy-ns rollout status deploy/ai-on-kubernetes
kubectl -n ai-proxy-ns get pods -l app=ai-on-kubernetes      # 1/1 Running
```

- The secret has no namespace in the file, so `-n ai-proxy-ns` is required — without it, it lands in `default` and the pod can't see it.
- The pod is created before the secret exists, so it shows `CreateContainerConfigError` for a minute and then starts on its own.
- **Leave the key out on AKS.** If the secret has `AZURE_OPENAI_API_KEY`, `src/openai_client.py` uses the key and Workload Identity is never exercised.

Check the webhook injected the identity:

```bash
POD=$(kubectl -n ai-proxy-ns get pod -l app=ai-on-kubernetes -o name | head -1)
kubectl -n ai-proxy-ns exec $POD -- env | grep -E '^AZURE_(CLIENT_ID|TENANT_ID|FEDERATED_TOKEN_FILE|AUTHORITY_HOST)='
kubectl -n ai-proxy-ns exec $POD -- env | grep -c '^AZURE_OPENAI_API_KEY='   # 0
```

## 6. Test (port-forward only — no public IP)

```bash
kubectl -n ai-proxy-ns port-forward svc/ai-on-kubernetes 8000:8000    # leave running

# second terminal:
curl -s http://localhost:8000/health
./probe_smoke.sh
BASE_URL=http://localhost:8000 uv run pytest tests/test_smoke.py tests/test_evals.py -m live -v
```

A `200` from `/v1/chat` with no key in the pod proves the identity chain: ServiceAccount token → Entra ID → `ai_on_aks` → OpenAI User role → model. Logs show `POST …/chat/completions "HTTP/1.1 200 OK"`.

Live tests call real Azure OpenAI and cost tokens. A public LoadBalancer is deferred until `/v1/chat` has auth — see [project-roadmap.md](project-roadmap.md#phase-8--api-auth--resilience).

## 7. Destroy (~5–15 min, mostly AKS)

```bash
# stop the port-forward first (Ctrl+C)
cd infra
export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
terraform plan -destroy           # expect: 8 to destroy
terraform destroy                 # don't Ctrl+C; if it fails, run it again

# verify
terraform state list                     # prints nothing
az group list --query "[].name" -o tsv   # no rg-terraform-ai-kubernetes, no MC_*

# kubeconfig cleanup
kubectl config use-context kind-kind
kubectl config delete-context ai-on-kubernetes-aks
kubectl config delete-cluster ai-on-kubernetes-aks
kubectl config delete-user clusterUser_rg-terraform-ai-kubernetes_ai-on-kubernetes-aks
```

Left behind on purpose (not Terraform-managed): `ai_aks_resource_group` (Azure OpenAI), `NetworkWatcherRG` and an empty `DefaultResourceGroup-EUS` (both auto-created by Azure, free).

## kubectl reference

### Contexts — which cluster am I talking to?

`~/.kube/config` holds three lists: **clusters** (API server URL + CA), **users** (credentials), and **contexts** (cluster + user pairs). `current-context` decides where every command goes.

```bash
kubectl config current-context              # check before every apply
kubectl config get-contexts
kubectl config use-context kind-kind        # or ai-on-kubernetes-aks
kubectl cluster-info                        # AKS: https://*.azmk8s.io ; Kind: https://127.0.0.1:<port>
```

`az aks get-credentials` adds all three entries; the user is `clusterUser_<rg>_<cluster>` (a client cert — this cluster uses local accounts, not Entra/kubelogin). They're stored separately, so cleanup deletes each one (step 7).

A running `port-forward` stays bound to the context it was **started** with — switching contexts doesn't move it. Prove where traffic goes by tailing that cluster's logs while you test.

### `-f` vs `-k`

| | `-f <path>` | `-k <dir>` |
|---|---|---|
| Input | Raw manifests, as written | Folder with a `kustomization.yaml` |
| On a folder | Applies every `.yaml` — including `kustomization.yaml` (fails: "kind/name not set") and `secret.yaml` | Only what's under `resources:` |
| Transforms | None | `images:`, `patches:` applied first |

Rule: `-f` for single plain manifests (`secret.yaml`); `-k` for any folder with a `kustomization.yaml`. Preview with `kubectl kustomize deployments/aks`; validate against the live cluster without changing anything with `kubectl apply -k deployments/aks --dry-run=server`.

### `-l` — select by label

Pods get `app: ai-on-kubernetes` from the Deployment template. `-l` is `--selector`; without it, kubectl treats `app=...` as a pod **name** (→ `NotFound`).

```bash
kubectl get pods -l app=ai-on-kubernetes --show-labels
kubectl logs -l app=ai-on-kubernetes --prefix
```

Syntax: `a=b`, `a!=b`, `'a in (x,y)'`, `a` (has key), `a=b,c=d` (AND). The label sits on the pod template, not on the Deployment/Service metadata — so `kubectl get deploy,svc -l app=...` shows nothing; use `kubectl get deploy,svc`.

### Services

```bash
kubectl get svc            # default namespace
kubectl get svc -A         # all: also kube-dns (cluster DNS), metrics-server (kubectl top)
kubectl get endpoints ai-on-kubernetes    # pod IPs the Service routes to — empty = selector mismatch
```

All ClusterIP (`EXTERNAL-IP <none>`) — nothing public.

### Logs vs events

| | Logs | Events |
|---|---|---|
| Written by | The app (stdout/stderr) | Kubernetes (scheduler, kubelet, controllers) |
| Answers | What did my app say? | What did the cluster do to my pod? |
| Use for | `CrashLoopBackOff` (`--previous`), request errors | `Pending`, `ImagePullBackOff`, `CreateContainerConfigError`, probe failures |
| Lifetime | Gone with the pod; `--previous` = one restart back | ~1 hour |

```bash
kubectl logs deploy/ai-on-kubernetes                 # one pod of the Deployment
kubectl logs deploy/ai-on-kubernetes -f | grep -v /health   # live, hide probe noise
kubectl logs deploy/ai-on-kubernetes --tail=50 --since=10m --timestamps
kubectl logs deploy/ai-on-kubernetes --previous      # the crashed container

kubectl get events --sort-by=.lastTimestamp          # unsorted by default
kubectl get events --field-selector type=Warning
kubectl get events -w                                # watch during apply/rollout
kubectl describe pod -l app=ai-on-kubernetes         # one object's events at the bottom
```

Paired `GET /health 200` lines every few seconds are the liveness + readiness probes from the node's kubelet.

## Debugging

| Symptom | Fix |
|---------|-----|
| `InvalidImageName` | Overlay still has the `<REGISTRY>` placeholder → step 4 |
| `ImagePullBackOff` | Overlay `newName` still points at an old ACR, or tag not pushed → steps 3–4 |
| `CrashLoopBackOff` + `exec format error` | arm64 image → rebuild with `--platform linux/amd64` |
| `CrashLoopBackOff` + pydantic `ValidationError` | Secret missing a key → fix `secret.yaml`, re-apply, `kubectl rollout restart deploy/ai-on-kubernetes` |
| `CreateContainerConfigError` | Secret not applied, or applied to `default` → step 5 (`-n ai-proxy-ns`) |
| `services "ai-on-kubernetes" not found` / `No resources found` | Forgot `-n ai-proxy-ns` |
| `ModuleNotFoundError` on start | `requirements.txt` not re-exported after `uv add` → step 3 |
| `DefaultAzureCredential failed to retrieve a token` | No `AZURE_*` env in the pod → pod label or `<CLIENT_ID>` missing (step 4); delete the pod after fixing |
| `AADSTS70021` / no matching federated identity | Namespace or ServiceAccount doesn't match the federated credential subject `system:serviceaccount:ai-proxy-ns:ai-proxy` |
| `401` / `PermissionDenied` from Azure OpenAI | Role assignment on the new identity still propagating — wait a few minutes |
| `kind not set` / `name not set` | Used `-f` on a kustomize folder → use `-k` |
| `subscription ID could not be determined` | `export ARM_SUBSCRIPTION_ID=...` |
| VM size not allowed / `InsufficientVCPUQuota` | Subscription limits; `Standard_D2als_v7` works here. B-series can't be an AKS system pool |
| `destroy` refuses to delete the RG | Something was created by hand in it → delete that, re-run destroy |
| `IMDSUnreachable` warning event on the node | Instance Metadata Service (`169.254.169.254`, used for managed-identity tokens incl. ACR pull) timed out at boot. Harmless if it stops and pods pull images; investigate only if the count keeps rising |
| `KubernetesDefaultServiceCIDRInconsistent` warning | One-off AKS creation noise; ignore |

Destroy timing: AKS takes ~5–10 of the 5–15 min (drains the node, deletes LB/IP/VNet/disks and the `MC_*` group). `Still destroying...` every 10 s is normal. Billing stops roughly when the node VM is deleted.

See [architecture.md](architecture.md) for why it's built this way.
