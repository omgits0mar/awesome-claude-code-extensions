# Trust and safety

Installing an agent extension can be equivalent to running code with your developer credentials. Directory presence, GitHub stars, a valid manifest, or an “official” provider badge is not a security review.

## Review before installation

Check:

- Automatic hooks and the lifecycle events that trigger them.
- Shell commands, package-manager invocations, downloaded scripts, and bundled binaries.
- Tool grants, filesystem scope, destructive operations, and permission bypasses.
- Network destinations, telemetry, update behavior, and dynamic code loading.
- Environment variables, tokens, browser sessions, SSH keys, cloud credentials, and production access.
- MCP tools that write, delete, deploy, purchase, message, or change permissions.
- Whether source and install artifacts are pinned to a tag, digest, commit, or checksum.
- The license that covers the exact plugin or subdirectory—not only the monorepo root.

Use a disposable environment for unfamiliar extensions. Prefer least-privilege and short-lived credentials. Keep destructive tools disabled until needed, and review every generated configuration before committing it.

## Catalog safety signals

The dataset records provenance and verification method. Planned enrichment fields include manifest validity, install checks, automatic hooks, shell execution, network access, credentials, bundled binaries, last release, archived status, and security review date.

We deliberately do not publish a generic “safe” badge.

## MCP-specific risks

MCP servers can expose powerful operations, accept untrusted content, change their advertised tools, or handle sensitive credentials. A hosted server also creates a data-sharing boundary. Verify the server source, transport, authentication, retention policy, and tool permissions.

The official MCP Registry verifies publisher namespaces but delegates package scanning and curation. Treat it as discovery metadata.

## Reporting

Follow [`SECURITY.md`](../SECURITY.md). Do not include working exploit details or secrets in a public issue.
