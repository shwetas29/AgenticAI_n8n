# n8n workflows — import order

1. Import specialists first: `01-discovery` … `06-certifier`
2. Import `00-orchestrator`
3. Create **Header Auth** credential for OpenAI (`Authorization: Bearer sk-...`) and attach to each `Call LLM` node (or set a shared credential).
4. Set env vars from `../config/env.example`
5. Optional: replace Execute Workflow name references if your n8n renames on import
6. Test with POST body = contents of `../samples/sample-a-regional-sales/intake.json`

## Webhooks

| Workflow | Path |
|---|---|
| Orchestrator | `POST /webhook/mstr-pbi/orchestrate` |
| Discovery | `POST /webhook/mstr-pbi/discover` |
| Assessor | `POST /webhook/mstr-pbi/assess` |
| Classifier | `POST /webhook/mstr-pbi/classify` |
| Transformer | `POST /webhook/mstr-pbi/transform` |
| Validator | `POST /webhook/mstr-pbi/validate` |
| Certifier | `POST /webhook/mstr-pbi/certify` |

HITL: when `requiresHumanApproval=true`, orchestrator **Wait** node pauses. Resume via the wait webhook with `{ "approved": true, "approver": "you@company.com" }`.
