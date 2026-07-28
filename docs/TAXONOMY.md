# Taxonomy

The catalog uses separate fields for **artifact form** and **capability category**.

## Artifact kinds

| Kind | Meaning |
| --- | --- |
| `plugin` | An installable client-native bundle that can include several component types; compatibility identifies the supported client. |
| `skill` | A progressively loaded instruction/resource package, usually centered on `SKILL.md`. |
| `command` | A reusable slash command, including legacy `.claude/commands` artifacts. |
| `hook` | Automation triggered by an agent client’s lifecycle events. |
| `agent` | A specialist subagent definition or agent collection. |
| `workflow` | A multi-step development, planning, or orchestration system. |
| `mcp-server` | A server exposing tools, resources, or prompts through MCP. |
| `mcp-tooling` | An MCP framework, gateway, registry, proxy, scanner, or manager. |
| `interface` | A GUI, IDE, mobile, remote, or terminal interface for Claude Code, Codex, or another cataloged client. |
| `monitoring` | Usage, cost, status-line, telemetry, or observability tooling. |
| `learning` | Documentation, examples, courses, or research. |
| `tool` | Supporting software that does not fit a narrower artifact kind. |
| `collection` | A marketplace, awesome list, or multi-project directory. |

One marketplace can contain hundreds of plugins; one plugin can contain skills, agents, hooks, commands, MCP servers, LSP servers, themes, and output styles. Counts therefore distinguish exact entries from unique GitHub repositories.

## Compatibility

- `claude-code`: Explicitly designed for or documented with Claude Code.
- `codex`: Explicitly designed for or documented with Codex.
- `agent-skills`: Uses the portable Agent Skills format.
- `mcp`: Uses the Model Context Protocol and can be configured in a compatible host.

Cross-agent projects are included only when Claude Code or Codex compatibility is explicit or follows directly from a supported open standard. A portable Agent Skill or standards-compliant MCP server may support both clients; Claude-native plugins, hooks, commands, interfaces, and status lines are not relabeled without separate evidence.

## Categories and tags

`category` preserves the source’s useful domain grouping, such as security, databases, browser automation, design, memory, DevOps, research, or communication. `tags` add normalized cross-cutting facets. Tags never replace the artifact kind.
