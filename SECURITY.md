# Security Policy

## Supported versions

Security fixes target the latest released version on the default branch.

## Reporting a vulnerability

Do not publish exploit details in a public issue. Contact the repository owner privately through GitHub's security advisory feature if enabled, or request a private reporting channel before sharing sensitive details.

## Current security boundaries

- Local-first, read-only repository indexing.
- Common secret files, generated folders, binaries, symlinks, and oversized files are excluded by default.
- Repository text is treated as data, not trusted instructions.
- This MVP does not execute shell commands or apply code patches.
- The API has no authentication. Bind it to loopback for local use; do not expose it to the public internet without authentication, authorization, rate limits, and a reviewed deployment design.

## Limitations

These controls are defense-in-depth, not a security certification. Review the threat model and run security tests before processing sensitive repositories.
