# Project Relay public MCP gateway

This small Render-compatible gateway gives the Project Relay MCP server a public host that can:

- forward Streamable HTTP MCP traffic to the Supabase broker;
- preserve Authorization and MCP protocol headers;
- expose a health endpoint at `/health`;
- expose the OpenAI domain-verification token at `/.well-known/openai-apps-challenge` when `OPENAI_APPS_CHALLENGE` is configured;
- rewrite protected-resource metadata and MCP authentication challenges to the public gateway MCP URL.

It stores no workstation or account credentials.

Render configuration:
- Runtime: Python
- Build: `python -m py_compile render_gateway.py`
- Start: `python render_gateway.py`
- Environment: `UPSTREAM_MCP=https://dbhwjzznwhukoogjewfl.supabase.co/functions/v1/project-relay-mcp`
