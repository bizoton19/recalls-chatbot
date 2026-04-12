using './main.bicep'

// ── Identity ──────────────────────────────────────────────────────────────────
param appName = 'cpsc-chatbot'

// Must be globally unique, 5-50 chars, alphanumeric only
// Change this to something unique before deploying
param acrName = 'cpscrecallsacr'

// ── Images (deploy.sh fills these in automatically) ──────────────────────────
// To deploy manually, set these to your pushed image tags:
//   <acrName>.azurecr.io/clip-service:latest
//   <acrName>.azurecr.io/backend:latest
//   <acrName>.azurecr.io/frontend:latest
param clipImage    = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param backendImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param frontendImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

// ── Secrets — fill these in before deploying ──────────────────────────────────
param databaseUrl        = ''   // your Railway DATABASE_URL
param azureOpenAiApiKey  = ''   // AZURE_OPENAI_API_KEY
param googleApiKey       = ''   // GOOGLE_API_KEY (for embeddings)

// ── Non-secret config ─────────────────────────────────────────────────────────
param azureOpenAiEndpoint   = 'https://cpsc-chatbot.openai.azure.com/'
param azureOpenAiDeployment = 'gpt-4o-mini'
param azureOpenAiApiVersion = '2024-08-01-preview'
param adminApiKey           = 'change-me-in-prod'
