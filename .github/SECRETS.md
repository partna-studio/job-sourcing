# GitHub Secrets Configuration

This document outlines the secrets that need to be configured in your GitHub repository for the CI/CD workflows to function properly.

## Setting Up Secrets

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Enter the secret name and value from the list below

## Required Secrets

### Core Service Configuration

#### `SERVICE_URL`
**Required by:** `all_users.yml`, `jobs.yml`

The base URL of your deployment service (where the Flask app is hosted).

**Example:**
```
https://example.com
```

### LinkedIn Authentication

#### `LI_TOKEN`
**Required by:** `jobs.yml`

LinkedIn `li_at` authentication token for accessing LinkedIn job data.

**Example:**
```
AQEDATrD6WsB3pWuAAABm-Y_gicAAAGclc5fGFYAGk7f5StMGaQgMX_w9qmkAxboNqvveHlW_ZmU1h8RSrkY0DNUtNGGhs2va1CczfKyyrC-CXX3-bWd1DTpIAuXLO1Ll3qyCWLv7tlkPOKZEIdwxsQ_
```

#### `JSESSION_ID`
**Required by:** `jobs.yml`

LinkedIn `JSESSIONID` cookie for authentication.

**Example:**
```
"ajax:4875800552991438397"
```

### Processing Configuration

#### `DEFAULT_MAX_WORKERS`
**Required by:** `all_users.yml` (optional, defaults to 2)

Maximum number of concurrent workers for processing multiple users.

**Example:**
```
2
```

#### `DEFAULT_MAX_USERS`
**Required by:** `all_users.yml` (optional, defaults to 0)

Maximum number of users to process. Use `0` for unlimited.

**Example:**
```
0
```

#### `RETRY_ATTEMPTS`
**Required by:** `all_users.yml`, `jobs.yml` (optional, defaults to 3)

Number of retry attempts for failed API calls.

**Example:**
```
3
```

#### `RETRY_SLEEP`
**Required by:** `all_users.yml`, `jobs.yml` (optional, defaults to 10)

Sleep duration in seconds between retry attempts.

**Example:**
```
10
```

### Notifications (Optional)

#### `NOTIFY_WEBHOOK`
**Required by:** `all_users.yml`, `jobs.yml` (optional)

Webhook URL for failure notifications. Leave empty to skip notifications.

**Example:**
```
https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

## Workflow-Specific Usage

### `all_users.yml` Workflow

This workflow requires:
- `SERVICE_URL` (required)
- `DEFAULT_MAX_WORKERS` (optional)
- `DEFAULT_MAX_USERS` (optional)
- `RETRY_ATTEMPTS` (optional)
- `RETRY_SLEEP` (optional)
- `NOTIFY_WEBHOOK` (optional)

**Trigger:** Runs automatically on Fridays at 10:00 UTC or manually via workflow dispatch.

**Parameters (when triggered manually):**
- `max_workers`: Override default max workers
- `max_users`: Limit number of users to process
- `uri`: Optional URI override for job fetch

### `jobs.yml` Workflow

This workflow requires:
- `SERVICE_URL` (required)
- `LI_TOKEN` (required or provide via input)
- `JSESSION_ID` (required or provide via input)
- `RETRY_ATTEMPTS` (optional)
- `RETRY_SLEEP` (optional)
- `NOTIFY_WEBHOOK` (optional)

**Trigger:** Manual workflow dispatch only.

**Parameters (when triggered manually):**
- `use_secrets`: If `true` (default), uses `LI_TOKEN` and `JSESSION_ID` secrets. If `false`, use input fields.
- `li_token`: LinkedIn token (if not using secrets)
- `j_session_id`: LinkedIn JSESSIONID (if not using secrets)

## Security Best Practices

1. **Never commit secrets** to your repository
2. **Rotate secrets regularly** for security credentials (tokens, API keys)
3. **Use resource-specific tokens** where possible (e.g., GitHub Personal Access Tokens with limited scopes)
4. **Monitor secret usage** in GitHub Actions logs (secrets are masked in logs)
5. **Use environment-specific secrets** if you have multiple deployments

## Troubleshooting

- **"ERROR: Set SERVICE_URL repository secret..."** → Add `SERVICE_URL` secret
- **"ERROR: LinkedIn tokens not provided"** → Ensure `LI_TOKEN` and `JSESSION_ID` secrets are set
- **Workflow fails silently** → Check that `SERVICE_URL` points to a running service
- **Notifications not working** → Verify `NOTIFY_WEBHOOK` URL is correct and accessible
