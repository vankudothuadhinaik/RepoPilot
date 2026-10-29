# Threat Model

## Assets
Repository source, local index database, engineering notes, provider credentials, and host filesystem.

## Trust boundaries
- Repository files are untrusted input.
- HTTP requests are untrusted input.
- Optional MCP callers are untrusted clients.
- The local process and database file are trusted only to the extent of the host account.

## Threats and mitigations
- Accidental secret ingestion: common secret filenames and key/certificate suffixes are excluded; users must review ignore rules.
- Symlink/path escape: symlinks are skipped during indexing and API file paths reject traversal.
- Prompt injection: this baseline does not ask an LLM to follow repository instructions; any future LLM integration must keep retrieved text as untrusted evidence.
- Unsafe execution: no shell execution or patch application is implemented.
- Network exposure: API defaults to loopback in CLI and Compose binds to 127.0.0.1.
- Unauthorized API access: `/api/*` routes require a constant-time bearer-token comparison; health endpoints are intentionally public for local monitoring. The token is sourced from Doppler in deployment and must not be committed or logged.
- Resource exhaustion: files are capped at 1 MB; there are still no comprehensive request/index rate limits.

## Residual risk
This document is a design record, not proof that all controls are effective. Run the security suite and review deployment settings before handling sensitive code.
