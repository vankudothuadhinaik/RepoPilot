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
- Symlink/path escape: symlinks are skipped, paths are checked against the selected root before reads, and file identity/size are checked around reads. These checks reduce race risk but are not a substitute for OS-level descriptor-relative no-follow traversal under an adversarial local writer.
- Prompt injection: optional LLM generation treats repository text as untrusted evidence and asks the model not to follow embedded instructions. Model output remains untrusted; path allowlisting rejects unknown citations but does not prove that every claim is supported.
- Unsafe execution: no shell execution or patch application is implemented.
- Network exposure: API defaults to loopback in CLI; Compose binds to 127.0.0.1. Compose refuses to render without a configured API bearer token.
- Unauthorized API access: `/api/*` routes require a constant-time-checked bearer token. This shared-token guard is not a user identity/role system and does not replace a reverse proxy, TLS, rate limits, or a security review.
- Resource exhaustion: individual files are capped at 1 MB and provider response/evidence payloads are bounded. There is no total repository byte/file-count budget, request rate limit, or independently validated large-repository resource envelope.

## Residual risk
This document is a design record, not proof that all controls are effective. Run the security suite and review deployment settings before handling sensitive code.
