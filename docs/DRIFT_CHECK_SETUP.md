# SwarmCity Drift Check — Setup Guide

The `swarm-drift-check.yml` workflow uses **AWS Bedrock (Amazon Nova Micro)** to assess
documentation drift between code changes and `.swarm/` state on every merge to `dev`/`prod`.

The quickest way to install it:

```bash
swarm setup-drift-check          # interactive — prompts for any missing secrets
swarm setup-drift-check --commit # also commits and pushes the workflow file
```

Or follow the manual steps below.

---

## 1. Enable Bedrock Model Access

1. AWS Console → **Amazon Bedrock** → **Model access**
2. Click **Modify model access** → enable **Amazon Nova Micro**
3. Submit (usually instant)

> Do this once per AWS account/region.

---

## 2. GitHub Secrets

The workflow reuses AWS credentials already present from deploy workflows.
Check **Settings → Secrets → Actions** for:

| Secret | Required | Notes |
|--------|----------|-------|
| `AWS_ACCESS_KEY_ID` | yes | IAM user key with `bedrock:InvokeModel` |
| `AWS_SECRET_ACCESS_KEY` | yes | Matching secret |
| `AWS_DEFAULT_REGION` | recommended | Defaults to `us-east-1` |

If the IAM user doesn't have Bedrock access, add this inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "bedrock:InvokeModel",
    "Resource": "arn:aws:bedrock:*::foundation-model/amazon.nova-micro-v1:0"
  }]
}
```

**Org-level secrets** (recommended): set once and all division repos inherit them.
GitHub Org → Settings → Secrets → Actions → New organization secret

---

## 3. Changing the Model

Set a repo/org **variable** (not secret) named `SWARM_BEDROCK_MODEL`:

| Model | Use case |
|-------|----------|
| `amazon.nova-micro-v1:0` | **Default** — fast, cheap |
| `anthropic.claude-3-5-sonnet-20241022-v2:0` | Deeper analysis |

```bash
gh variable set SWARM_BEDROCK_MODEL --body "anthropic.claude-3-5-sonnet-20241022-v2:0"
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Bedrock invocation failed` | Check IAM `bedrock:InvokeModel` policy; check region |
| `Could not load credentials` | AWS secrets not set |
| `AccessDeniedException` | Enable model access in Bedrock console (step 1) |
| Comment not posted | Workflow needs `pull-requests: write` permission |
