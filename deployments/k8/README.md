# Kind manifests — learning guide

**Status (Sep 2026):** Phase 3 manual path works — Kind cluster, image loaded, Deployment + Service + Secret applied, pod **Ready 1/1**, `/health` via port-forward. **Next:** finish learning drills, then automate smoke (SDET).

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
| `port` | Port on the Service (door) |
| `targetPort` | Port on the container (inside the room) |

**ClusterIP** (default) = reachable inside the cluster. On Kind you reach it with **port-forward** (a process on your laptop).

```bash
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
| **Restart port-forward** after Service networking changes | Apply updates the Service; your laptop tunnel does not auto-refresh |
| **`kubectl describe`** | Deep dive + Events (probes, image pull). Use when `get` looks wrong |
| **Images on Kind** | `docker exec kind-control-plane crictl images` — not the same as host `docker images` |
| **Probes in logs** | Repeated `GET /health` often = kubelet readiness/liveness checks |

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
| Image errors | `kind load docker-image` + `crictl images` |

---

## Learning drills

**Original three (you already did these before the README refresh):**

1. [x] Wrong Service `app:` label → apply → empty endpoints / broken forward → fix  
2. [x] Typo the `image:` name → `describe pod` / ImagePullBackOff or ErrImageNeverPull  
3. [x] `kubectl delete -f deployments/k8/` → re-apply  

**Added in the README update (optional — only if you want more practice):**

4. [ ] Break probe path to `/broken` → Ready 0/1 → fix *(new)*  
5. [ ] Rewrite `service.yaml` from memory (~10 lines) and compare *(new)*  

---

## What's next (directions)

**Still Phase 3:**

1. Confirm chat works through the tunnel (if you haven’t yet):
   ```bash
   curl -s http://localhost:8000/v1/chat \
     -H "Content-Type: application/json" -X POST \
     -d '{"messages":[{"role":"user","content":"hello"}]}'
   ```
2. Optional: drills 4–5 above (probe break + rewrite Service from memory).
3. Practice saying out loud: Deployment / Pod / Service / Secret / readiness vs liveness / port-forward.

**Then SDET (roadmap Tier 1):**

4. Automate smoke: `scripts/smoke.sh` or `tests/smoke/` — `/health` + `/v1/chat` after apply.
5. **Phase 5 — Thin CI** — GitHub Actions: pytest on PR + build image (high resume ROI).
6. Phase 8 evals later; Phase 4 AKS after Kind smoke is scripted.

See [docs/project-roadmap.md](../../docs/project-roadmap.md) — SDET track + Phase 3 checklist.
