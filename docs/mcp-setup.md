# MCP setup

Install the optional dependency:

```bash
pip install -e ".[mcp]"
```

Run the server from the same environment and data directory as the API:

```bash
python -m repopilot.mcp_server
```

The server currently exposes `list_repositories`, `search_code`, `find_symbol`, `repository_overview`, and `retrieve_memory`. Configure your MCP client using its documented stdio server configuration format. The server reads the local RepoPilot SQLite database and does not execute repository commands.
