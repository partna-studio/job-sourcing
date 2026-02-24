GitHub Workflows for job-sourcing service

This file documents the two workflows added to call your deployed service endpoints.

Required repository secrets
- `SERVICE_URL` (required): Base URL of your running service, e.g. https://my-app.example.com

Optional secrets
- `LI_TOKEN`, `JSESSION_ID`: LinkedIn tokens for the `/api/jobs` workflow when `use_secrets=true`.
- `DEFAULT_MAX_WORKERS`: default for `/api/all_users` when not provided via dispatch inputs.
- `DEFAULT_MAX_USERS`: default for `/api/all_users` when not provided via dispatch inputs.
- `NOTIFY_WEBHOOK`: optional webhook URL to POST failure notifications to (will receive a small JSON payload). The payload includes a `response_b64` field containing the base64-encoded response body.
- `RETRY_ATTEMPTS`: number of retry attempts for HTTP calls (default `3`).
- `RETRY_SLEEP`: seconds to sleep between attempts (default `10`).

How the workflows run
- `.github/workflows/all_users.yml`
  - Runs on schedule: Fridays at 05:00 AM EST (cron `0 10 * * FRI`) and supports manual dispatch via the Actions UI.
  - Dispatch inputs: `max_workers` (default 2), `max_users` (0 = all), `uri` (optional). Values may be overridden by `DEFAULT_*` secrets.
  - On repeated failures the workflow will post a JSON to `NOTIFY_WEBHOOK` (if set). The JSON contains `workflow`, `status`, `http`, and `response_b64`.

- `.github/workflows/jobs.yml`
  - Manual `workflow_dispatch` only.
  - Inputs: `use_secrets` (default `true`), `li_token`, `j_session_id` (used if `use_secrets=false`). If `use_secrets=true`, `LI_TOKEN` and `JSESSION_ID` secrets are used.
  - On repeated failures the workflow will post a JSON to `NOTIFY_WEBHOOK` (if set) including `response_b64`.

Running locally vs in GitHub Actions
- These workflows assume your service is reachable at `SERVICE_URL` (set as a secret in the repo settings).
- For local testing run the Flask app and then use the `requests` snippets in code or `curl` to hit the endpoints.

Example `curl` to trigger `/api/all_users` manually (for local testing):

```bash
curl -X POST "http://localhost:5000/api/all_users" -H "Content-Type: application/json" -d '{"max_workers":2, "max_users":3}'
```

If you want I can add an example GitHub Actions `workflow_dispatch` API curl example to this README.
