# Troubleshooting

- **No results:** confirm the repository appears in `repopilot repos`, re-index it, and try an exact identifier.
- **No Python symbols:** Python AST parsing is the only implemented symbol parser in this MVP.
- **FTS5 errors:** use a plain identifier query; the search implementation quotes query tokens and falls back to substring search on FTS syntax errors.
- **API unavailable:** check `repopilot serve`, then visit `/health/ready`.
- **Secrets not excluded:** review `src/repopilot/security.py` and add patterns to `.gitignore`; no secret scanner can detect every custom credential filename.
- **MCP cannot see repositories:** ensure API and MCP process share `REP_PILOT_DATA_DIR`.
