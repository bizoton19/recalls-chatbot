# Deployment Guide — Railway

This app deploys as **3 Railway services** from a single GitHub repository:

```
recalls-chatbot (GitHub repo)
├── backend/    → Railway service: "backend"
├── frontend/   → Railway service: "frontend"
└── (database)  → Railway PostgreSQL plugin
```

---

## Step 1 — Create GitHub Repository

On GitHub.com, create a new **empty** repository named `recalls-chatbot`.
Then push the local code:

```bash
cd /Users/alex/recalls-chatbot
git remote add origin https://github.com/YOUR_USERNAME/recalls-chatbot.git
git push -u origin master
```

---

## Step 2 — Create Railway Project

1. Go to [railway.app](https://railway.app) → **New Project**
2. Select **Deploy from GitHub repo**
3. Choose `recalls-chatbot`
4. Railway will detect the repo — **do not let it auto-deploy yet**

---

## Step 3 — Add PostgreSQL Database

1. In your Railway project, click **+ New** → **Database** → **PostgreSQL**
2. Railway provisions Postgres with **pgvector pre-installed**
3. Note the `DATABASE_URL` — Railway auto-injects this into other services

---

## Step 4 — Configure Backend Service

In Railway project → click the auto-created service → **Settings**:

| Setting | Value |
|---------|-------|
| **Root Directory** | `backend` |
| **Build Command** | *(auto via nixpacks)* |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Health Check Path** | `/health` |

**Environment Variables** (Variables tab):

| Variable | Value | Notes |
|----------|-------|-------|
| `GOOGLE_API_KEY` | `AIza...` | Gemini chat + text embeddings (RAG); one key for both |
| `LLM_PROVIDER` | `google` | Or: openai, anthropic, groq, openrouter, ollama |
| `LLM_MODEL` | `gemini-2.0-flash` | Or another Gemini model id |
| `EMBEDDING_PROVIDER` | `google` | Default; use `openai` only if you index with OpenAI embeddings |
| `EMBEDDING_MODEL` | *(omit)* | Defaults to `models/text-embedding-004` when `EMBEDDING_PROVIDER=google` |
| `EMBEDDING_DIMENSIONS` | `1536` | Must match `recall_embeddings` column; do not change after first index |
| `OPENAI_API_KEY` | *(omit)* | Only if `LLM_PROVIDER=openai` or `EMBEDDING_PROVIDER=openai` |
| `CORS_ORIGINS` | `https://YOUR-FRONTEND.up.railway.app` | Set after frontend deploys |
| `ADMIN_API_KEY` | *(generate a strong random string)* | Protects /api/admin/ingest |
| `INGESTION_SCHEDULE_HOURS` | `6` | How often to re-sync CPSC data |
| `DATABASE_URL` | *(auto-injected by Railway from Postgres plugin)* | Reference variable from the DB service |

---

## Step 5 — Configure Frontend Service

In Railway → **+ New** → **GitHub Repo** → same repo → **Settings**:

| Setting | Value |
|---------|-------|
| **Root Directory** | `frontend` |
| **Build Command** | `npm ci && npm run build` |
| **Start Command** | `node .next/standalone/server.js` |
| **Health Check Path** | `/` |

**Environment Variables**:

| Variable | Value | Notes |
|----------|-------|-------|
| `NEXT_PUBLIC_API_URL` | `https://YOUR-BACKEND.up.railway.app` | Backend public URL from Step 4 |
| `NODE_ENV` | `production` | |
| `PORT` | `3000` | Railway injects $PORT but set as fallback |

> **Important**: `NEXT_PUBLIC_API_URL` is baked into the frontend at build time.
> Set it **before** the first deploy. If you change the backend URL later, redeploy the frontend.

---

## Step 6 — Deploy

1. Trigger deploy on **backend** first — wait for `/health` to return `{"status": "ok"}`
2. Copy the backend's **Public URL** from Railway dashboard
3. Set `NEXT_PUBLIC_API_URL` on frontend service to that URL
4. Set `CORS_ORIGINS` on backend service to the frontend's public URL
5. Trigger deploy on **frontend**

Both services auto-redeploy on every push to `master`.

---

## Step 7 — Run Full Historical Sync (One-Time)

After first deploy, seed the database with all CPSC recalls (~30 years):

```bash
curl -X POST https://YOUR-BACKEND.up.railway.app/api/admin/ingest \
  -H "x-admin-key: YOUR_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"full_sync": true}'
```

This runs in the background (~10–20 min). Check logs in Railway dashboard.
After that, the scheduler re-syncs recent recalls every 6 hours automatically.

---

## Estimated Monthly Cost (Railway)

| Service | Cost |
|---------|------|
| Backend (512MB RAM) | ~$5 |
| Frontend (512MB RAM) | ~$5 |
| PostgreSQL (1GB) | ~$5 |
| **Total** | **~$15/month** |

Railway offers $5 free credit/month — prototype costs ~$10/month net.

---

## Environment Variables — Quick Reference

### Backend (copy-paste into Railway Variables tab)

```
GOOGLE_API_KEY=AIza...
LLM_PROVIDER=google
LLM_MODEL=gemini-2.0-flash
EMBEDDING_PROVIDER=google
CORS_ORIGINS=https://YOUR-FRONTEND.up.railway.app
ADMIN_API_KEY=change-me-to-a-strong-random-string
INGESTION_SCHEDULE_HOURS=6
```

### Frontend (copy-paste into Railway Variables tab)

```
NEXT_PUBLIC_API_URL=https://YOUR-BACKEND.up.railway.app
NODE_ENV=production
PORT=3000
```
