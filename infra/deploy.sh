#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# CPSC Recalls Chatbot — Azure Container Apps deploy script
#
# Usage:
#   ./infra/deploy.sh [--resource-group <rg>] [--location <loc>] [--tag <tag>]
#
# Prerequisites:
#   az login
#   az account set --subscription <your-subscription-id>
#
# On first run this script:
#   1. Creates the resource group (if needed)
#   2. Deploys infra (ACR + env) with placeholder images
#   3. Builds & pushes all 3 Docker images to ACR
#   4. Re-deploys with real image tags + updates CORS origins
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config (edit these or pass as args) ──────────────────────────────────────
RESOURCE_GROUP="${RESOURCE_GROUP:-cpsc-chatbot-rg}"
LOCATION="${LOCATION:-eastus}"
ACR_NAME="${ACR_NAME:-cpscrecallsacr}"      # must match main.bicepparam
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo latest)}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# ── Parse optional args ───────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
    --location)       LOCATION="$2";       shift 2 ;;
    --tag)            IMAGE_TAG="$2";      shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "▶ Resource group : $RESOURCE_GROUP"
echo "▶ Location       : $LOCATION"
echo "▶ ACR            : $ACR_NAME"
echo "▶ Image tag      : $IMAGE_TAG"
echo ""

# ── 1. Create resource group ──────────────────────────────────────────────────
echo "── Step 1/5: Ensure resource group exists ──"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
echo "   ✓ $RESOURCE_GROUP"

# ── 2. First-pass deploy (placeholder images — creates ACR so we can push) ───
echo "── Step 2/5: Deploy infrastructure (ACR + Container Apps env) ──"
az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file  "$REPO_ROOT/infra/main.bicep" \
  --parameters     "$REPO_ROOT/infra/main.bicepparam" \
  --output none
echo "   ✓ Infrastructure ready"

# ── 3. Build & push images ────────────────────────────────────────────────────
echo "── Step 3/5: Login to ACR and push images ──"
az acr login --name "$ACR_NAME"

BACKEND_URL=$(az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name main \
  --query properties.outputs.backendUrl.value -o tsv)

CLIP_IMAGE="$ACR_NAME.azurecr.io/clip-service:$IMAGE_TAG"
BACKEND_IMAGE="$ACR_NAME.azurecr.io/backend:$IMAGE_TAG"
FRONTEND_IMAGE="$ACR_NAME.azurecr.io/frontend:$IMAGE_TAG"

echo "   Building clip-service…"
docker build -t "$CLIP_IMAGE" "$REPO_ROOT/clip-service"
docker push "$CLIP_IMAGE"

echo "   Building backend…"
docker build -t "$BACKEND_IMAGE" "$REPO_ROOT/backend"
docker push "$BACKEND_IMAGE"

echo "   Building frontend (NEXT_PUBLIC_API_URL=$BACKEND_URL)…"
docker build \
  --build-arg "NEXT_PUBLIC_API_URL=$BACKEND_URL" \
  -t "$FRONTEND_IMAGE" \
  "$REPO_ROOT/frontend"
docker push "$FRONTEND_IMAGE"

echo "   ✓ All images pushed to $ACR_NAME"

# ── 4. Re-deploy with real images ─────────────────────────────────────────────
echo "── Step 4/5: Deploy container apps with real images ──"
az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file  "$REPO_ROOT/infra/main.bicep" \
  --parameters     "$REPO_ROOT/infra/main.bicepparam" \
  --parameters \
    clipImage="$CLIP_IMAGE" \
    backendImage="$BACKEND_IMAGE" \
    frontendImage="$FRONTEND_IMAGE" \
  --output none
echo "   ✓ Container apps updated"

# ── 5. Patch CORS origins with the real frontend URL ─────────────────────────
echo "── Step 5/5: Update backend CORS_ORIGINS ──"
FRONTEND_URL=$(az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name main \
  --query properties.outputs.frontendUrl.value -o tsv)

az containerapp update \
  --name           "cpsc-chatbot-backend" \
  --resource-group "$RESOURCE_GROUP" \
  --set-env-vars   "CORS_ORIGINS=$FRONTEND_URL" \
  --output none
echo "   ✓ CORS_ORIGINS → $FRONTEND_URL"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════"
echo "  Deploy complete!"
echo "  Backend  : $BACKEND_URL"
echo "  Frontend : $FRONTEND_URL"
echo "══════════════════════════════════════════"
