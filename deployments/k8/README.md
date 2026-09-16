# Kind manifests — learning guide

**Status (Sep 2026):** Phases 3–5 done (Kind + CI + eval harness + live golden evals). **Next:** Phase 6 AKS (see [project-roadmap.md](../../docs/project-roadmap.md)).

Three small files. Read top-to-bottom in this order.

## 1. `secret.example.yaml` — config (secrets)

Like `.env`, but for Kubernetes.

| Field | Your app uses it for |
|-------|----------------------|
| `AZURE_OPENAI_ENDPOINT` | Where to call Azure |
| `AZURE_OPENAI_API_KEY` | Auth |
| `AZURE_OPENAI_MODEL` | Which deployment |
| `AZURE_OPENAI_API_VERSION` | API version |

```bash
cp secret.example.yaml secret.yaml   # secret.yaml is gitignored
# edit secret.yaml — paste from your .env
```

The Deployment loads this via `secretRef: azure-openai`.

---

## 2. `deployment.yaml` — run the container

| Field | Meaning |
|-------|---------|
| `replicas: 1` | One copy of your app |
| `image` | Docker image name (must match `docker build -t ...`) |
| `imagePullPolicy: Never` | Kind only — use the image you loaded locally |
| `containerPort: 8000` | Port uvicorn listens on |
| `livenessProbe` | Restart container if `/health` fails (app stuck/dead) |
| `readinessProbe` | Don't send traffic until `/health` passes (`Ready 0/1` → `1/1`) |

The label `app: ai-on-kubernetes` appears in three places — Deployment selector, pod template, and Service selector. **They must match.**

---

## 3. `service.yaml` — access door (ClusterIP)

A Service is a **stable access door** to pods — not automatically open to the public internet.

| Field | Meaning |
|-------|---------|
| `selector.app` | Which pods get traffic (must match Deployment labels) |
| `port` | Port on the **Service** (what clients / port-forward dial) |
| `targetPort` | Port on the **pod/container** (where the app listens) |

Flow: `client → Service:port → Pod:targetPort`. They can differ (e.g. Service `9000` → pod `8000`); this app usually keeps both `8000`.

**ClusterIP** (default) = reachable inside the cluster — not the public internet. On Kind you reach it with **port-forward** (a process on your laptop).

```bash
# localPort:servicePort  →  then Service maps servicePort → targetPort
kubectl port-forward svc/ai-on-kubernetes 8000:8000
curl http://localhost:8000/health
```

---

## Concepts you already hit (keep these)

| Idea | Takeaway |
|------|----------|
| **Kind vs kubectl** | Kind creates the cluster; kubectl talks to it |
| **Service ≠ public internet** | ClusterIP is internal; port-forward is a local tunnel |
| **port-forward is a process** | Not a cluster object. Dies if you Ctrl+C / close terminal. Check: `ps aux \| grep 'kubectl port-forward'` or `lsof -i :8000` |
| **Wrong Service selector** | Pod stays Running — check `kubectl get endpoints` (empty). Fix label match |
| **Service without a selector** | Duplicate `spec:` in YAML keeps only the last block — selector dropped → port-forward fails. One `spec:` with selector + ports |
| **`port` vs `targetPort`** | Service door vs container listen port. port-forward uses `local:servicePort` |
| **Restart port-forward** after Service networking changes | Apply updates the Service; your laptop tunnel does not auto-refresh |
| **`kubectl describe`** | Deep dive + Events (probes, image pull). Use when `get` looks wrong |
| **Images on Kind** | `docker exec kind-control-plane crictl images` — not the same as host `docker images` |
| **Probes in logs** | Repeated `GET /health` often = kubelet readiness/liveness checks |
| **readiness vs liveness** | Ready gate (no traffic) vs restart stuck container. Controllers keep `replicas` — they don't spawn forever from a bad readiness probe |

---

## Apply (in order)

```bash
# 1. secret (once)
cp deployments/k8/secret.example.yaml deployments/k8/secret.yaml
# fill in secret.yaml

# 2. image (rebuild if code/Dockerfile changed)
docker build -t ai-on-kubernetes:local .
kind load docker-image ai-on-kubernetes:local

# 3. manifests
kubectl apply -f deployments/k8/

# 4. check
kubectl get deploy,pods,svc
kubectl port-forward svc/ai-on-kubernetes 8000:8000
# other terminal:
curl http://localhost:8000/health
```

---

## kubectl cheat sheet

```bash
kubectl get deploy,pods,svc
kubectl get pods -l app=ai-on-kubernetes
kubectl describe pod <name>
kubectl logs <name>
kubectl get endpoints ai-on-kubernetes
kubectl get all -l app=ai-on-kubernetes

# port-forward
kubectl port-forward svc/ai-on-kubernetes 8000:8000
ps aux | grep 'kubectl port-forward' | grep -v grep
lsof -i :8000

# Kind images
docker exec kind-control-plane crictl images | grep ai-on-kubernetes
```

---

## If something breaks

| Symptom | Check |
|---------|--------|
| `curl: connection refused` on localhost:8000 | Is port-forward running? |
| port-forward "lost connection to pod" | Pod restarted — start port-forward again |
| Ready 0/1 | `describe pod` — probe failing? App still starting? |
| Service but no traffic | `kubectl get endpoints` — empty = label mismatch |
| `Service is defined without a selector` | YAML has two `spec:` keys; merge into one with `selector` + `ports` |
| port-forward works but wrong app port | Check `local:servicePort` matches Service `port`, and `targetPort` matches the container |
| Image errors | `kind load docker-image` + `crictl images` |

---

## Learning drills

**Original three (you already did these before the README refresh):**

1. [x] Wrong Service `app:` label → apply → empty endpoints / broken forward → fix  
2. [x] Typo the `image:` name → `describe pod` / ImagePullBackOff or ErrImageNeverPull  
3. [x] `kubectl delete -f deployments/k8/` → re-apply  

**Added later (done):**

4. [x] Break probe path → Ready 0/1 → fix  
5. [x] Rewrite `service.yaml` (paste/modify OK) — hit duplicate `spec:` / missing selector → fix  

---

## What's next (directions)

**Phase 3 smoke (done):**

1. Start the tunnel (leave it running):
   ```bash
   kubectl port-forward svc/ai-on-kubernetes 8000:8000
   ```
2. In another terminal (venv activated):
   ```bash
   ./probe_smoke.sh
   ```
   That runs `pytest tests/test_smoke.py -v -m live` against `BASE_URL` (`http://localhost:8000`).

**Then SDET (roadmap Tier 1):**

3. [x] **Phase 4 — Thin CI** — mocked pytest + docker build on GitHub Actions.
4. [x] **Phase 5 — Thin evals** — mocked CI + `@pytest.mark.live` httpx golden path.
5. **Phase 6 — AKS** — ACR + Terraform.

See [docs/project-roadmap.md](../../docs/project-roadmap.md).
