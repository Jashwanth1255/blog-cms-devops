# Blog CMS — DevOps Course-Based Project

A Blog/CMS REST API (posts and comments) taken through the full DevOps lifecycle: Git and GitHub, Docker, Docker Compose, Kubernetes, GitHub Actions, Postman, Prometheus and Grafana, and Terraform.

| Layer | Tool |
|---|---|
| Application | Python 3.12, Flask, SQLAlchemy |
| Database | PostgreSQL 16 (SQLite when run without Docker) |
| Source control | Git + GitHub |
| Containers | Docker, Docker Compose |
| Orchestration | Kubernetes (Minikube), HPA autoscaling |
| CI | GitHub Actions |
| API testing | Postman |
| Monitoring and logging | Prometheus, Grafana, structured JSON logs |
| Infrastructure as Code | Terraform (Docker provider) |

## Project structure

```
blog-cms-devops/
├── app/                      # Exercise 1, 5
│   ├── app.py                # Flask REST API
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
├── docker-compose.yml        # Exercise 5, 12: API + Postgres + Prometheus + Grafana
├── k8s/                      # Exercise 6, 7
│   ├── 00-namespace.yaml
│   ├── 01-config.yaml        # Secret + ConfigMap
│   ├── 02-postgres.yaml      # PVC + Deployment + Service
│   ├── 03-api.yaml           # Deployment + NodePort Service + HPA
│   └── 04-monitoring.yaml    # Prometheus + Grafana in the cluster
├── .github/workflows/ci-cd.yml   # Exercise 8
├── postman/Blog-CMS-API.postman_collection.json   # Exercise 10
├── monitoring/               # Exercise 12
│   ├── prometheus.yml
│   └── grafana/              # auto-provisioned datasource + dashboard
└── terraform/                # Exercise 13
    ├── main.tf
    ├── variables.tf
    └── outputs.tf
```

## Install these first

- Git, Python 3.10+, Docker Desktop
- Minikube and kubectl
- Postman
- Terraform

Check them:

```bash
git --version && python --version && docker --version
minikube version && kubectl version --client && terraform -version
```

---

## Exercise 1 — Backend with CRUD APIs

Run it locally (uses SQLite, no database setup needed):

```bash
cd app
python -m venv .venv
# Windows: .venv\Scripts\activate     Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The API is now at http://localhost:5000.

| Method | Endpoint | What it does |
|---|---|---|
| GET | `/api/posts` | List posts (filters: `?published=true`, `?author=sai`) |
| GET | `/api/posts/<id>` | Get one post |
| POST | `/api/posts` | Create a post (`title`, `content` required) |
| PUT | `/api/posts/<id>` | Replace a post (full update) |
| PATCH | `/api/posts/<id>` | Change only the fields you send |
| DELETE | `/api/posts/<id>` | Delete a post and its comments |
| GET | `/api/posts/<id>/comments` | List comments on a post |
| POST | `/api/posts/<id>/comments` | Add a comment (`body` required) |
| PATCH | `/api/comments/<id>` | Edit a comment |
| DELETE | `/api/comments/<id>` | Delete a comment |
| GET | `/health` | Health check (also checks the database) |
| GET | `/metrics` | Prometheus metrics |

Quick check with curl:

```bash
curl -X POST http://localhost:5000/api/posts -H "Content-Type: application/json" -d "{\"title\":\"Hello\",\"content\":\"First post\"}"
curl http://localhost:5000/api/posts
curl -X PATCH http://localhost:5000/api/posts/1 -H "Content-Type: application/json" -d "{\"published\":true}"
curl -X DELETE http://localhost:5000/api/posts/1
```

---

## Exercises 2 and 3 — Git, GitHub and source code management

### One-time setup

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

### Create the repo and push

Create an empty repo named `blog-cms-devops` on GitHub (no README), then:

```bash
cd blog-cms-devops
git init
git add .
git commit -m "Initial commit: Blog CMS API with DevOps setup"
git branch -M main
git remote add origin https://github.com/<your-username>/blog-cms-devops.git
git push -u origin main
```

### Commands to explore (screenshot each for your report)

```bash
git status                 # what changed
git log --oneline --graph  # commit history
git diff                   # unstaged changes
git show HEAD              # last commit in detail
git remote -v              # linked remotes
```

### Practice with the code: feature branch, merge, pull request

```bash
# 1. New branch for a feature
git checkout -b feature/search-endpoint

# 2. Make a change in app/app.py, e.g. add this endpoint above `if __name__ == "__main__":`
#
#    @app.get("/api/posts/search")
#    def search_posts():
#        q = request.args.get("q", "")
#        posts = Post.query.filter(Post.title.ilike(f"%{q}%")).all()
#        return jsonify([p.to_dict() for p in posts])

git add app/app.py
git commit -m "Add post search endpoint"
git push -u origin feature/search-endpoint
```

On GitHub: open a Pull Request from `feature/search-endpoint` into `main`, have a teammate review, then merge. Then locally:

```bash
git checkout main
git pull origin main
git branch -d feature/search-endpoint
```

### More SCM operations to demonstrate

```bash
# Undo the last commit but keep the changes
git reset --soft HEAD~1

# Revert a pushed commit safely (creates a new commit)
git revert <commit-hash>

# Save work in progress without committing
git stash
git stash pop

# Tag a release
git tag -a v1.0.0 -m "First release"
git push origin v1.0.0

# Merge conflict practice: two branches edit the same line of app.py,
# merge one, then merge the other and resolve the conflict markers
git checkout -b teammate-a   # edit the "version" text in index(), commit
git checkout main
git checkout -b teammate-b   # edit the same line differently, commit
git checkout main && git merge teammate-a
git merge teammate-b         # conflict → fix the file → git add app/app.py → git commit
```

Team workflow: each member works on their own branch and opens a PR. Turn on branch protection for `main` (Settings → Branches) so nothing is merged without a review and a passing CI run.

---

## Exercise 4 — Docker commands

```bash
docker version
docker pull postgres:16-alpine           # download an image
docker images                            # list images
docker run -d --name test-nginx -p 8080:80 nginx   # run a container
docker ps                                # running containers
docker ps -a                             # all containers
docker logs test-nginx                   # container logs
docker exec -it test-nginx sh            # shell inside the container
docker stats                             # live CPU/memory
docker inspect test-nginx                # full details
docker stop test-nginx && docker rm test-nginx
docker rmi nginx                         # remove image
docker system prune                      # clean up unused stuff
```

---

## Exercise 5 — Containerize the application

Build and run only the API:

```bash
docker build -t blog-cms-api:latest ./app
docker run -d --name blog-api -p 5000:5000 blog-cms-api:latest
curl http://localhost:5000/health
docker logs blog-api
docker rm -f blog-api
```

Run the full stack (API + PostgreSQL + Prometheus + Grafana):

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f api
```

| Service | URL |
|---|---|
| API | http://localhost:5000 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin / admin) |

Stop with `docker compose down` (add `-v` to also delete the database volume).

Key Dockerfile points to mention: slim base image, dependency layer cached before code copy, non-root user, `HEALTHCHECK`, and Gunicorn as the production server.

---

## Exercises 6 and 7 — Kubernetes with Docker, and automating the containerized app

```bash
minikube start --driver=docker
minikube addons enable metrics-server     # needed for autoscaling

# Build the image and load it into Minikube
docker build -t blog-cms-api:latest ./app
minikube image load blog-cms-api:latest

# Deploy everything
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/

# Watch it come up
kubectl get all -n blog
kubectl -n blog rollout status deployment/blog-api
```

Open the API:

```bash
minikube service blog-api -n blog --url
# or: kubectl -n blog port-forward svc/blog-api 5000:5000
```

### What Kubernetes automates (demo each)

**Self-healing:** delete a pod and watch Kubernetes replace it.

```bash
kubectl get pods -n blog
kubectl delete pod <blog-api-pod-name> -n blog
kubectl get pods -n blog -w
```

**Scaling:**

```bash
kubectl scale deployment blog-api -n blog --replicas=4
kubectl get pods -n blog
```

**Autoscaling (HPA):** generate load and watch pods increase from 2 up to 5.

```bash
kubectl get hpa -n blog -w
# in a second terminal:
kubectl run load -n blog --rm -it --image=busybox:1.36 --restart=Never -- \
  sh -c "while true; do wget -q -O- http://blog-api:5000/api/posts > /dev/null; done"
```

**Rolling update and rollback:**

```bash
kubectl set env deployment/blog-api -n blog APP_VERSION=1.1.0
kubectl rollout status deployment/blog-api -n blog
kubectl rollout history deployment/blog-api -n blog
kubectl rollout undo deployment/blog-api -n blog
```

**Logs and debugging:**

```bash
kubectl logs -n blog -l app=blog-api --tail=20
kubectl describe pod <pod-name> -n blog
```

Clean up: `kubectl delete namespace blog` and `minikube stop`.

---

## Exercise 8 — GitHub Actions setup

The workflow is in `.github/workflows/ci-cd.yml` and runs on every push and pull request to `main`. It has three jobs:

1. **build**: installs dependencies, lints with flake8, starts the app and checks `/health`.
2. **docker**: builds the Docker image and pushes it to Docker Hub (only on `main`).
3. **deploy-test**: creates a temporary Kubernetes cluster with kind, deploys the manifests, and calls the live API.

To enable the Docker Hub push:

1. Create a Docker Hub access token (Account Settings → Personal access tokens).
2. In your GitHub repo: Settings → Secrets and variables → Actions → New repository secret.
3. Add `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`.

Without these secrets the image still builds but isn't pushed, so the pipeline stays green.

To explore the environment: open the **Actions** tab, click a run, expand each step's logs, and use **Re-run jobs**. You can also start it manually with **Run workflow** (enabled by `workflow_dispatch`).

---

## Exercise 10 — Postman manual API testing

1. Open Postman → **Import** → choose `postman/Blog-CMS-API.postman_collection.json`.
2. Make sure the API is running (local, Docker Compose, or port-forwarded from Kubernetes).
3. `baseUrl` is set to `http://localhost:5000` in the collection variables. Change it for Minikube (use the URL from `minikube service blog-api -n blog --url`) or Terraform (`http://localhost:5001`).
4. Send the requests one by one, top to bottom. Create stores the new post id in `postId`, so later requests use it automatically.
5. To run everything at once: right-click the collection → **Run collection**. Each request has a status-code check that shows pass/fail.

The collection covers GET, POST, PUT, PATCH, and DELETE, plus the 400 (missing fields) and 404 (deleted post) error cases.

---

## Exercise 12 — Monitoring and logging dashboards

### Metrics (Prometheus + Grafana)

The app exposes `/metrics` with:

- `flask_http_request_total`: request count by method and status
- `flask_http_request_duration_seconds`: latency histogram by endpoint
- `blog_posts_created_total`: posts successfully created
- `blog_app_info`: running version

With Docker Compose running:

1. Prometheus: http://localhost:9090 → **Status → Targets** shows `blog-api` as UP. Try the query `rate(flask_http_request_total[1m])`.
2. Grafana: http://localhost:3000 (admin / admin) → **Dashboards → Blog CMS → Blog CMS API**. The datasource and dashboard load automatically.
3. Generate traffic so the graphs move: run the Postman collection with 20+ iterations.

On Kubernetes, `k8s/04-monitoring.yaml` deploys Prometheus (scrapes every API pod separately) and Grafana:

```bash
minikube service grafana -n blog --url      # admin / admin
```

Import the dashboard there with **Dashboards → New → Import** → upload `monitoring/grafana/dashboards/blog-dashboard.json`.

### Logging

Every request is logged as one JSON line (method, path, status, duration), which log tools such as Loki or ELK can parse.

```bash
docker compose logs -f api
kubectl logs -n blog -l app=blog-api -f
```

---

## Exercise 13 — Terraform

`terraform/` creates the same stack (network, volume, PostgreSQL, API built from `app/`) as Docker containers, using the Docker provider. No cloud account needed.

```bash
cd terraform
terraform init       # downloads the Docker provider
terraform fmt        # formats the files
terraform validate   # checks syntax
terraform plan       # previews what will be created
terraform apply      # type "yes"
terraform output     # shows the API URL (http://localhost:5001)
terraform state list # resources Terraform manages
```

On Windows, uncomment the `host = "npipe:..."` line in `main.tf` first.

Things to try:

- Change `app_version` in `terraform.tfvars` (copy from `terraform.tfvars.example`) and run `terraform plan` to see what changes.
- Edit `app.py`, then `terraform apply`: the image rebuilds because of the file-hash trigger.
- Override a variable from the command line: `terraform apply -var="api_port=5002"`.
- `terraform destroy` removes everything.

---

## Demo script (about 10 minutes)

1. Show the repo, branches, and a merged pull request on GitHub.
2. Push a small change → show the GitHub Actions run passing.
3. `docker compose up -d --build` → run the Postman collection → open the Grafana dashboard.
4. Deploy to Minikube → delete a pod (self-healing) → run the load test (HPA scales up).
5. `terraform apply` → show the API on port 5001 → `terraform destroy`.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ErrImageNeverPull` / `ImagePullBackOff` in Minikube | Run `minikube image load blog-cms-api:latest` again |
| HPA shows `<unknown>` targets | `minikube addons enable metrics-server`, wait a minute |
| API pod stuck in `Init` | Database pod isn't ready yet; check `kubectl get pods -n blog` |
| Port 5000 already in use (Mac) | Turn off AirPlay Receiver, or change `"5000:5000"` to `"5050:5000"` in compose |
| Grafana dashboard empty | Generate some traffic; check Prometheus targets are UP |
| Terraform can't reach Docker | Make sure Docker Desktop is running; on Windows use the `npipe` host line |
