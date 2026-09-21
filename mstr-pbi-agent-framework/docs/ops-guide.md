# Operations guide

## Prerequisites

- n8n 1.60+ (Cloud or self-hosted)
- LLM API key (OpenAI or Azure OpenAI)
- Optional: MicroStrategy REST, Fabric/Power BI service principal
- Optional: Postgres or n8n Data Tables for evidence persistence

## Import

1. In n8n: **Workflows → Import from File**
2. Import in order listed in `n8n-workflows/README.md`
3. Open each specialist workflow → `Call LLM (JSON mode)` → set Header Auth credential
4. Confirm Execute Workflow nodes in `00-orchestrator` resolve by workflow **name**

## Configure

Copy `config/env.example` into n8n environment variables (or `.env` for self-hosted).

Minimum:

```
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1
FRAMEWORK_VERSION=1.0.0
DEFAULT_TARGET_PLATFORM=fabric
```

For Azure OpenAI, point `OPENAI_BASE_URL` to your Azure deployments base and adjust the HTTP node URL if needed.

## Run a sample

### Offline (no n8n)

```bash
cd mstr-pbi-agent-framework
python3 scripts/run_offline_pipeline.py --sample all
python3 scripts/run_offline_pipeline.py --sample c --approve
```

Outputs land in `out/*.bundle.json`.

### n8n

POST intake JSON to the orchestrator webhook, or paste a sample into Manual Trigger via a Set node.

Example:

```bash
curl -X POST "$N8N_URL/webhook/mstr-pbi/orchestrate" \
  -H 'content-type: application/json' \
  -d @samples/sample-a-regional-sales/intake.json
```

## HITL

If `classification.requiresHumanApproval` is true, execution waits.

Resume payload:

```json
{ "approved": true, "approver": "lead@company.com", "notes": "Security pattern accepted" }
```

Rejection (`approved: false`) halts before Transform and writes a halted evidence bundle.

## Evidence

Each run accumulates:

- `intake` / `inventory`
- `assessment`
- `classification`
- `blueprint`
- `validation`
- `certification`
- `decisionLog[]`

Persist the final node output to Postgres/Sheet/Data Table for programme reporting.

## Wave operations

1. Batch intakes into a queue (one item = one reportId)
2. Run orchestrator per item with concurrency limits (LLM rate limits)
3. Route `review` / `hand_build` lanes to delivery pod boards using `priority` + `wave`
4. Only promote to Certify when validation blockers are pass/waived
