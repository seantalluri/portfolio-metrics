# Portfolio Metrics

Public-safe activity indicators for private product repositories.

These assets are intentionally sanitized. They expose **no source code, commit messages, branch names, SHAs, authors, issue titles, diffs, filenames, credentials, or internal implementation details**.

## Current badges

- `metrics/pm-gold.svg`
- `metrics/ce-control-plane.svg`
- `metrics/ezra.svg`
- `metrics/koinonia.svg`
- `metrics/christ-everywhere.svg`

The current badges indicate that development is active while keeping the underlying repositories private.

## Planned automation

Each private repository can publish aggregate metrics into this public repository using a narrowly scoped write token that has access **only** to this public metrics repository. The private repository's built-in GitHub Actions token reads its own activity; the publishing token never needs read access to the private source repository.

When enabled, the generated assets can safely report aggregate values such as commit count, pull-request count, release count, and last-updated time without exposing private development content.