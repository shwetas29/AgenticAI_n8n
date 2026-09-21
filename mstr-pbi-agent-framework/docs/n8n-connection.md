# Connect to n8n

This framework talks to n8n over HTTP:

| Need | Endpoint |
|---|---|
| Health | `GET {N8N_BASE_URL}/healthz` |
| Public API | `GET/POST {N8N_BASE_URL}/api/v1/...` + header `X-N8N-API-KEY` |
| Orchestrator run | `POST {N8N_BASE_URL}/webhook/mstr-pbi/orchestrate` |

## Option A — local n8n in this environment

```bash
# already started by the agent when available
export N8N_BASE_URL=http://127.0.0.1:5678
python3 scripts/n8n_connect.py status
```

1. Open the n8n editor URL printed in the start log (or `http://127.0.0.1:5678`).
2. Complete owner setup once.
3. Create an API key: **Settings → API → Create API key**.
4. Export it and import workflows:

```bash
export N8N_API_KEY=...
python3 scripts/n8n_connect.py import
```

## Option B — your existing n8n Cloud / self-hosted

```bash
export N8N_BASE_URL=https://YOUR_INSTANCE.app.n8n.cloud   # or https://n8n.yourcompany.com
export N8N_API_KEY=your_api_key
python3 scripts/n8n_connect.py status
python3 scripts/n8n_connect.py import
```

Then attach OpenAI/Azure credentials on each `Call LLM` node (or a shared credential) and activate `00-orchestrator`.

## Helper CLI

```bash
python3 scripts/n8n_connect.py status
python3 scripts/n8n_connect.py workflows
python3 scripts/n8n_connect.py import [--activate]
python3 scripts/n8n_connect.py trigger --intake samples/sample-a-regional-sales/intake.json
```

Copy `config/n8n.connection.example.env` to a local env file; do not commit secrets.
