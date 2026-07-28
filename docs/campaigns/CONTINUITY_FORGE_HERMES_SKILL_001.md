# CONTINUITY_FORGE_HERMES_SKILL_001

## Intent

Ship install/setup docs and a Hermes-ready operator skill so the agentic path
uses MCP + mutation contracts without owning canon.

## Status

```text
setup_docs: PASS
hermes_skill: PASS
build_skill_prompt: PASS
mcp_readme: PASS
```

## Artifacts

| Path | Role |
|------|------|
| `docs/SETUP.md` | Install, env, UI, MCP, Docker |
| `docs/hermes/README.md` | Hermes integration |
| `docs/hermes/mcp.example.json` | MCP stdio config example |
| `docs/hermes/BUILD_SKILL_PROMPT.md` | Meta-prompt to rebuild skill |
| `skills/hermes-continuity-forge/` | Operator skill + references |

## Non-goals

- Implementing Hermes runtime inside this repo
- Real production media generation
- Autonomous director agent without shot contracts
