# Remote MCP classroom

`server.py` uses FastMCP 4.0.5 over streamable HTTP. It verifies three separate opaque tokens and enforces `notes:read` or `notes:write` plus server-derived ownership. `client.py` is a real HTTP client. Notes are intentionally held in memory and reset when the server restarts.

Run the complete network test from the notebook root with `.venv/Scripts/python labs/remote-mcp/test_remote.py`. It creates random test credentials, selects a free loopback port, verifies seven groups of behavior, saves `test-report.json`, and stops its process tree.

For manual use, set three distinct random secrets of at least 24 characters in `MCP_ALICE_READ_TOKEN`, `MCP_ALICE_WRITE_TOKEN`, and `MCP_BOB_READ_TOKEN`. Run `server.py`; it binds to `127.0.0.1:8093` by default. In the client terminal set `MCP_CLIENT_TOKEN` to the desired credential and run `client.py`. Optional `MCP_URL` chooses another server URL. The token itself is never a tool argument.

The Dockerfile is a deployment recipe using a non-root user. Build it from this folder and provide secrets at runtime. Bind the published port to loopback for local use. For access beyond loopback, configure TLS, deployment-specific host/origin policy, proper identity issuance and rotation, concurrency limits, logging and health checks. This static verifier is not a public OAuth authorization server. The recorded container acceptance test targets Study Coach; it does not establish that this separate MCP Dockerfile was built. This MCP project's own network-test evidence is in test-report.json.
