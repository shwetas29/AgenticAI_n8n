#!/usr/bin/env python3
"""
n8n connection helper for the MSTR→PBI agent framework.

Supports:
  - health check
  - create/list API keys (owner login flow when possible)
  - import workflows from n8n-workflows/
  - list workflows
  - trigger orchestrator webhook

Env:
  N8N_BASE_URL   default http://127.0.0.1:5678
  N8N_API_KEY    required for most Public API calls
  N8N_EMAIL / N8N_PASSWORD  optional owner credentials for setup
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF_DIR = ROOT / "n8n-workflows"


def load_local_env():
    env_path = ROOT / "config" / "n8n.local.env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


load_local_env()
DEFAULT_BASE = os.environ.get("N8N_BASE_URL", "http://127.0.0.1:5678").rstrip("/")


class N8nClient:
    def __init__(self, base_url: str = DEFAULT_BASE, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("N8N_API_KEY")

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        headers: dict | None = None,
        api: bool = True,
    ):
        url = f"{self.base_url}{path}"
        hdrs = {"Accept": "application/json", **(headers or {})}
        if api and self.api_key:
            hdrs["X-N8N-API-KEY"] = self.api_key
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            hdrs["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode() or "{}"
                return resp.status, json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            try:
                payload = json.loads(err) if err else {"message": str(e)}
            except json.JSONDecodeError:
                payload = {"message": err or str(e)}
            return e.code, payload
        except urllib.error.URLError as e:
            return 0, {"message": f"connection failed: {e.reason}"}

    def health(self):
        # /healthz is available on many n8n builds; fall back to root
        status, payload = self._request("GET", "/healthz", api=False)
        if status == 0:
            return status, payload
        if status >= 400:
            status, payload = self._request("GET", "/", api=False)
        return status, payload if isinstance(payload, dict) else {"ok": status == 200}

    def list_workflows(self):
        return self._request("GET", "/api/v1/workflows")

    def create_workflow(self, workflow: dict):
        # Public API expects a reduced payload
        payload = {
            "name": workflow["name"],
            "nodes": workflow.get("nodes", []),
            "connections": workflow.get("connections", {}),
            "settings": workflow.get("settings") or {"executionOrder": "v1"},
            "staticData": workflow.get("staticData"),
        }
        return self._request("POST", "/api/v1/workflows", body=payload)

    def activate_workflow(self, workflow_id: str, active: bool = True):
        # Some versions use PATCH; others POST /activate
        status, payload = self._request(
            "PATCH",
            f"/api/v1/workflows/{workflow_id}",
            body={"active": active},
        )
        if status >= 400:
            action = "activate" if active else "deactivate"
            status, payload = self._request("POST", f"/api/v1/workflows/{workflow_id}/{action}")
        return status, payload

    def import_framework_workflows(self, activate: bool = False):
        order = [
            "01-discovery.json",
            "02-assessor.json",
            "03-classifier.json",
            "04-transformer.json",
            "05-validator.json",
            "06-certifier.json",
            "00-orchestrator.json",
        ]
        results = []
        existing_status, existing = self.list_workflows()
        by_name = {}
        if existing_status == 200:
            for wf in existing.get("data", existing if isinstance(existing, list) else []):
                by_name[wf.get("name")] = wf

        for fname in order:
            path = WF_DIR / fname
            if not path.exists():
                results.append({"file": fname, "ok": False, "error": "missing file"})
                continue
            doc = json.loads(path.read_text())
            name = doc["name"]
            if name in by_name:
                results.append(
                    {
                        "file": fname,
                        "ok": True,
                        "skipped": True,
                        "id": by_name[name].get("id"),
                        "name": name,
                    }
                )
                continue
            status, payload = self.create_workflow(doc)
            item = {
                "file": fname,
                "ok": status in (200, 201),
                "status": status,
                "name": name,
                "id": (payload.get("id") if isinstance(payload, dict) else None),
                "response": payload,
            }
            if item["ok"] and activate and item["id"]:
                a_status, a_payload = self.activate_workflow(str(item["id"]), True)
                item["activated"] = a_status in (200, 201)
                item["activateResponse"] = a_payload
            results.append(item)
        return results

    def trigger_orchestrator(self, intake: dict, path: str = "mstr-pbi/orchestrate"):
        # Production webhook path when workflow is active
        return self._request("POST", f"/webhook/{path}", body=intake, api=False)


def cmd_status(client: N8nClient, _args):
    status, payload = client.health()
    print(json.dumps({"baseUrl": client.base_url, "httpStatus": status, "payload": payload}, indent=2))
    return 0 if status and status < 500 else 1


def cmd_workflows(client: N8nClient, _args):
    status, payload = client.list_workflows()
    print(json.dumps({"httpStatus": status, "payload": payload}, indent=2))
    return 0 if status == 200 else 1


def cmd_import(client: N8nClient, args):
    if not client.api_key:
        print("N8N_API_KEY is required for import. Create one in n8n Settings → API, or pass --api-key.", file=sys.stderr)
        return 2
    results = client.import_framework_workflows(activate=args.activate)
    print(json.dumps(results, indent=2))
    return 0 if all(r.get("ok") for r in results) else 1


def cmd_trigger(client: N8nClient, args):
    intake = json.loads(Path(args.intake).read_text())
    status, payload = client.trigger_orchestrator(intake)
    print(json.dumps({"httpStatus": status, "payload": payload}, indent=2))
    return 0 if status and status < 400 else 1


def main():
    parser = argparse.ArgumentParser(description="Connect to n8n for MSTR→PBI framework")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--api-key", default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_status = sub.add_parser("status", help="Check n8n reachability")
    p_status.set_defaults(func=cmd_status)

    p_wf = sub.add_parser("workflows", help="List workflows via Public API")
    p_wf.set_defaults(func=cmd_workflows)

    p_imp = sub.add_parser("import", help="Import framework workflows")
    p_imp.add_argument("--activate", action="store_true")
    p_imp.set_defaults(func=cmd_import)

    p_trig = sub.add_parser("trigger", help="POST intake to orchestrator webhook")
    p_trig.add_argument("--intake", required=True)
    p_trig.set_defaults(func=cmd_trigger)

    args = parser.parse_args()
    client = N8nClient(base_url=args.base_url, api_key=args.api_key)
    raise SystemExit(args.func(client, args))


if __name__ == "__main__":
    main()
