# KoboToolbox Synchronous Export Proxy

A secure, simplified proxy for connecting KoboToolbox Synchronous Exports to Power BI and other tools.

## Overview

This Cloudflare Worker proxies requests to KoboToolbox's "Synchronous Export" API. It allows you to:

1.  **Securely share data**: Map API keys to specific export settings without sharing your main Kobo credentials.
2.  **Simplify Power BI connection**: Use a stable URL with query parameter authentication, avoiding complex header configurations in Power Query.
3.  **Control access**: Grant granular access to specific saved exports (e.g., "Partner A" only sees the "Partner A Export" settings).

## Architecture

```
Power BI (Web Connector) 
       ↓
Cloudflare Worker (Validates Key & Permissions from Secret)
       ↓
KoboToolbox API (Fetches Pre-generated Export)
       ↓
Returns CSV/Excel File
```

## Setup & Deployment

### 1. Prerequisites
-   **Cloudflare Account**: You need a Cloudflare account to deploy the worker.
-   **Wrangler CLI**: Install via `npm install -g wrangler`.
-   **KoboToolbox Account**: You need an Admin Token from Kobo.

### 2. Configure Permissions
Permissions are stored in a secure Cloudflare Worker Secret named `PROXY_PERMISSIONS`.

1.  Create a local file named `permissions.json` (do not commit this to git):
    ```json
    {
      "partner-agency-key": {
        "name": "Partner Agency A",
        "allowed": [
          { 
            "asset": "aiBgJcvz5AFHB54fKpG2y5",
            "setting": "esuPrAsvJANYiJ6jZcA9KM9"
          }
        ]
      }
    }
    ```
    *   **asset**: The Kobo Asset UID (found in the form URL).
    *   **setting**: The Export Setting UID (found in Kobo's API or URL when editing an export).

2.  Upload the permissions:
    ```bash
    wrangler secret put PROXY_PERMISSIONS < permissions.json
    ```

### 3. Set Kobo Token
Set your KoboToolbox Admin Token as a secret:
```bash
wrangler secret put KOBO_API_TOKEN
# Paste your token when prompted
```

### 4. Deploy
```bash
wrangler deploy
```

## Usage

### URL Structure
```
https://<your-worker-subdomain>.workers.dev/exports/<ASSET_UID>/<EXPORT_SETTING_UID>/<FORMAT>?api_key=<YOUR_KEY>
```

*   **FORMAT**: `csv` or `xlsx`

### Example
```bash
curl "https://kobo-proxy.example.workers.dev/exports/aiBgJcvz5AFHB54fKpG2y5/esuPrAsvJANYiJ6jZcA9KM9/csv?api_key=partner-agency-key"
```

## Power BI Integration

### Method 1: Web Connector (Recommended)
1.  In Power BI Desktop, click **Get Data** -> **Web**.
2.  Select **Advanced**.
3.  Enter the full URL with the API key:
    `https://.../exports/.../csv?api_key=partner-agency-key`
4.  Click **OK**.
5.  Select **Anonymous** authentication (the key is in the URL).

### Method 2: Power Query (M Code)
For more control, use this M code in the Advanced Editor:

```powerquery
let
    BaseUrl = "https://your-worker.workers.dev",
    AssetUid = "aiBgJcvz5AFHB54fKpG2y5",
    ExportSettingUid = "esuPrAsvJANYiJ6jZcA9KM9",
    ApiKey = "partner-agency-key",
    
    FullUrl = BaseUrl & "/exports/" & AssetUid & "/" & ExportSettingUid & "/csv?api_key=" & ApiKey,
    
    Source = Csv.Document(Web.Contents(FullUrl), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    #"Promoted Headers"
```

## Troubleshooting

*   **"Access to the resource is forbidden" (403) in Power BI**:
    *   **Cause 1: Cloudflare WAF / Bot Fight Mode**: Cloudflare often blocks Power BI's User-Agent (`Microsoft.Data.Mashup`).
        *   **Fix**: Go to your Cloudflare Dashboard -> Security -> WAF. Check the "Firewall Events" log. If you see blocked requests from Power BI, create a Custom Rule to **Skip** the WAF for requests where the User Agent contains `Microsoft.Data.Mashup`. Alternatively, disable "Bot Fight Mode".
    *   **Cause 2: Stale Credentials**:
        *   **Fix**: Go to **File** -> **Options and settings** -> **Data source settings**. Select the entry for your worker URL and click **Clear Permissions**. Then try connecting again, ensuring you select **Anonymous**.
    *   **Cause 3: Invalid Key**: Ensure the API key in your URL matches exactly what is in `permissions.json`.

*   **Invalid API Key**: Check that your key exists in the `permissions.json` you uploaded.
*   **Access Denied**: Ensure the key is allowed to access the specific Asset UID and Export Setting UID requested.
*   **Upstream Error**: If Kobo returns an error, the proxy will pass it through. Check if the Export Setting UID is valid and the export has been generated in Kobo.

## License
MIT
