# Portfolio Metrics

Public-safe activity indicators for private product repositories.

These assets are intentionally sanitized. They expose **no source code, commit messages, branch names, SHAs, authors, issue titles, diffs, filenames, credentials, or internal implementation details**.

## Published badges

- `metrics/pm-gold.svg`
- `metrics/ce-control-plane.svg`
- `metrics/ezra.svg`
- `metrics/koinonia.svg`
- `metrics/christ-everywhere.svg`

Once automation is enabled, each badge reports both:

- **Lifetime:** commits + pull requests
- **Last 30 days:** commits + pull requests

A companion JSON file is published beside each SVG using the same slug.

## Security model

Each private repository reads its own activity with its built-in `GITHUB_TOKEN`. A separate fine-grained token named `PORTFOLIO_PUBLISH_TOKEN` is used only to write the aggregate result into this public repository.

The publishing token should have:

- Repository access: **only `seantalluri/portfolio-metrics`**
- Repository permission: **Contents — Read and write**
- No access to the private source repositories

This separation means the credential capable of publishing public badges cannot read the private code it is summarizing.

## Refresh cadence

Private caller workflows refresh metrics:

- after pushes to `main`;
- on a staggered weekly schedule;
- on manual `workflow_dispatch` runs.

## Public payload

Only these values leave the private repository:

```json
{
  "label": "Product name",
  "visibility": "private",
  "window_days": 30,
  "lifetime": {
    "commits": 0,
    "pull_requests": 0
  },
  "last_30_days": {
    "commits": 0,
    "pull_requests": 0
  },
  "updated_at": "UTC timestamp"
}
```

The publisher deliberately does **not** emit repository names, commit text, PR titles, identities, SHAs, branches, filenames, diffs, issues, or source content.
