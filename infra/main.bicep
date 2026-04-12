/*
  CPSC Recalls Chatbot — Azure Container Apps deployment
  Resources created:
    - Azure Container Registry (Basic)
    - Log Analytics Workspace
    - Container Apps Environment
    - Container App: clip-service  (internal, ViT-B/32 CLIP model)
    - Container App: backend       (public, FastAPI)
    - Container App: frontend      (public, Next.js)

  Deploy with: ./deploy.sh  (first run) or az deployment group create ... (subsequent)
*/

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Short name prefix used for all resources')
param appName string = 'cpsc-chatbot'

@description('Azure Container Registry name (must be globally unique, alphanumeric)')
param acrName string

// ── Image tags (set by deploy.sh after push) ─────────────────────────────────
@description('Full image reference for the CLIP service, e.g. <acr>.azurecr.io/clip-service:latest')
param clipImage string

@description('Full image reference for the backend, e.g. <acr>.azurecr.io/backend:latest')
param backendImage string

@description('Full image reference for the frontend, e.g. <acr>.azurecr.io/frontend:latest')
param frontendImage string

// ── Secrets ───────────────────────────────────────────────────────────────────
@secure()
param databaseUrl string

@secure()
param azureOpenAiApiKey string

param azureOpenAiEndpoint string
param azureOpenAiDeployment string = 'gpt-4o-mini'
param azureOpenAiApiVersion string = '2024-08-01-preview'

@secure()
param googleApiKey string

param adminApiKey string = 'change-me-in-prod'
param ingestionScheduleHours string = '6'

// ── Container Registry ────────────────────────────────────────────────────────
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: true }
}

// ── Log Analytics (required by Container Apps) ────────────────────────────────
resource logs 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${appName}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ── Container Apps Environment ────────────────────────────────────────────────
resource env 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${appName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

// ── Shared ACR pull secret (reused by all three apps) ─────────────────────────
var acrPassword = acr.listCredentials().passwords[0].value
var acrUsername = acr.listCredentials().username

// ── CLIP Service (internal — only backend needs to reach it) ──────────────────
resource clipApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${appName}-clip'
  location: location
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: false  // not reachable from the public internet
        targetPort: 8001
      }
      registries: [{ server: acr.properties.loginServer, username: acrUsername, passwordSecretRef: 'acr-pwd' }]
      secrets: [{ name: 'acr-pwd', value: acrPassword }]
    }
    template: {
      containers: [{
        name: 'clip'
        image: clipImage
        resources: { cpu: json('1.0'), memory: '2Gi' }
        env: []
        probes: [{
          type: 'Startup'
          httpGet: { path: '/health', port: 8001 }
          initialDelaySeconds: 20
          periodSeconds: 10
          failureThreshold: 12   // allow 2 min for model to load on cold start
        }]
      }]
      scale: { minReplicas: 0, maxReplicas: 2 }
    }
  }
}

// Internal FQDN for the CLIP service (used by backend env var)
var clipInternalUrl = 'http://${clipApp.properties.configuration.ingress.fqdn}'

// ── Backend (FastAPI) ─────────────────────────────────────────────────────────
resource backendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${appName}-backend'
  location: location
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
      }
      registries: [{ server: acr.properties.loginServer, username: acrUsername, passwordSecretRef: 'acr-pwd' }]
      secrets: [
        { name: 'acr-pwd',       value: acrPassword }
        { name: 'database-url',  value: databaseUrl }
        { name: 'oai-key',       value: azureOpenAiApiKey }
        { name: 'google-key',    value: googleApiKey }
      ]
    }
    template: {
      containers: [{
        name: 'backend'
        image: backendImage
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'DATABASE_URL',               secretRef: 'database-url' }
          { name: 'LLM_PROVIDER',               value: 'azure' }
          { name: 'AZURE_OPENAI_ENDPOINT',      value: azureOpenAiEndpoint }
          { name: 'AZURE_OPENAI_DEPLOYMENT',    value: azureOpenAiDeployment }
          { name: 'AZURE_OPENAI_API_VERSION',   value: azureOpenAiApiVersion }
          { name: 'AZURE_OPENAI_API_KEY',       secretRef: 'oai-key' }
          { name: 'EMBEDDING_PROVIDER',         value: 'google' }
          { name: 'EMBEDDING_DIMENSIONS',       value: '768' }
          { name: 'GOOGLE_API_KEY',             secretRef: 'google-key' }
          { name: 'CLIP_SERVICE_URL',           value: clipInternalUrl }
          { name: 'ADMIN_API_KEY',              value: adminApiKey }
          { name: 'INGESTION_SCHEDULE_HOURS',   value: ingestionScheduleHours }
          // CORS_ORIGINS is updated after the frontend URL is known (see deploy.sh)
          { name: 'CORS_ORIGINS',               value: 'http://localhost:3000' }
        ]
      }]
      scale: { minReplicas: 0, maxReplicas: 3 }
    }
  }
}

// ── Frontend (Next.js) ────────────────────────────────────────────────────────
resource frontendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${appName}-frontend'
  location: location
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: true
        targetPort: 3000
      }
      registries: [{ server: acr.properties.loginServer, username: acrUsername, passwordSecretRef: 'acr-pwd' }]
      secrets: [{ name: 'acr-pwd', value: acrPassword }]
    }
    template: {
      containers: [{
        name: 'frontend'
        image: frontendImage
        resources: { cpu: json('0.25'), memory: '0.5Gi' }
        env: [
          // NEXT_PUBLIC_API_URL is baked into the image at build time (see deploy.sh)
          // Runtime var for server-side fetch (SSR) — not the same as the baked public one
          { name: 'NEXT_PUBLIC_API_URL', value: 'https://${backendApp.properties.configuration.ingress.fqdn}' }
        ]
      }]
      scale: { minReplicas: 0, maxReplicas: 3 }
    }
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────
output acrLoginServer string = acr.properties.loginServer
output backendUrl string = 'https://${backendApp.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output clipInternalUrl string = clipInternalUrl
