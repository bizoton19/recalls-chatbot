# Azure deployment (Bicep + Container Apps)

## Parameter file (secrets)

`main.bicepparam` is **not committed** — it can hold API keys and org-specific names.

1. Copy the example and edit locally:

   ```bash
   cp infra/main.bicepparam.example infra/main.bicepparam
   ```

2. Fill in `databaseUrl`, `azureOpenAiApiKey`, `googleApiKey`, and adjust `appName`, `acrName`, and Azure OpenAI endpoint/deployment to match your subscription.

3. Run `./infra/deploy.sh` (see script header for `az login` and resource group options).

The example file uses placeholders only and is safe for a public repository.
