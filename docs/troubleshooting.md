# Troubleshooting

- **No results:** confirm the repository appears in `repopilot repos`, re-index it, and try an exact identifier.
- **No Python symbols:** Python AST parsing is the only implemented symbol parser in this MVP.
- **FTS5 errors:** use a plain identifier query; the search implementation quotes query tokens and falls back to substring search on FTS syntax errors.
- **API unavailable:** for Docker, run `doppler run -- docker compose ps` and `doppler run -- docker compose logs repopilot`, then visit `http://127.0.0.1:8010/health/ready`. The container still listens on port 8000 internally. For the local CLI, check `doppler run -- repopilot serve` and use port 8000.
- **Host port conflict:** do not stop unrelated services. Change only the host side of the Compose mapping (for example, `127.0.0.1:8011:8000`) and update the dashboard proxy and documented URL; keep the container side at `:8000`.
- **Doppler secrets:** verify the selected project/config with `doppler configure get project config`, then run Compose through `doppler run -- docker compose ...`. Do not write a secret-bearing `.env` file or print `REP_PILOT_API_TOKEN`.
- **401 from `/api/*`:** obtain the token through Doppler in memory and send it as `Authorization: Bearer <token>`. `/health/live` and `/health/ready` remain public. Compose refuses to start when the Doppler token is missing or empty.
- **Docker cannot find a host repository:** the default Compose service cannot see arbitrary host paths. Register a path visible inside the container, use the local Python API for host files, or add an explicitly reviewed read-only bind mount; do not assume a Windows path is available in Linux containers.
- **Secrets not excluded:** review `src/repopilot/security.py` and add patterns to `.gitignore`; no secret scanner can detect every custom credential filename.
- **MCP cannot see repositories:** ensure API and MCP process share `REP_PILOT_DATA_DIR`.
