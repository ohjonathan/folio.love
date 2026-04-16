---
id: infra-bootstrap
version: 1.0.0
role: meta-prompt
audience: [worker, human-operator]
wraps: 01-worker-session-contract.md (when run by a worker)
required_tokens:
  - ARTIFACT_OUTPUT_PATHS
optional_tokens:
  - CONTROL_PLANE_HOST
  - CONTROL_PLANE_OS
  - SESSION_TOOL
  - REMOTE_ACCESS_TOOL
  - POWER_RESILIENCE_TOOL
  - PACKAGE_MANIFEST
  - FAMILY_CLI_MAP
  - PR_TOOL
depends_on: [framework.md, 01-worker-session-contract.md]
---

# Infrastructure Bootstrap Meta-Prompt

For standing up the control-plane host that runs the orchestrator and hosts
long-lived sessions. Hardware- and OS-specific; fill in tokens before
dispatch.

## BEGIN INFRA BOOTSTRAP

**Your role.** You are the infra-bootstrap worker (or a human operator
following this runbook). You establish a reproducible baseline on the
control-plane host so that orchestrator sessions survive reboots, network
blips, and power events.

**Target host.** `<CONTROL_PLANE_HOST>` running `<CONTROL_PLANE_OS>`.

**Sections required.**

1. **OS system config** — sleep/wake, firewall, remote login, time sync.
   Desired state is stateless: write the commands that produce it, not the
   current state.
2. **Network & remote access** — static address or mesh VPN, SSH key
   policy, port exposure via `<REMOTE_ACCESS_TOOL>`.
3. **Session resilience** — `<SESSION_TOOL>` (e.g., tmux / screen /
   systemd-run) configuration so orchestrator sessions survive disconnects.
4. **Power resilience** — `<POWER_RESILIENCE_TOOL>` (UPS, smart plug,
   shutdown hooks) so the host recovers cleanly from power events.
5. **Service supervision** — init system unit (launchd, systemd) that
   restarts the orchestrator on crash and on boot.
6. **Remote IDE / interactive access** — optional: VS Code / IntelliJ
   remote-SSH config for debugging sessions.
7. **Package baseline** — `<PACKAGE_MANIFEST>` (Brewfile, apt list,
   requirements.txt, etc.).
8. **Dotfiles** — reference to the dotfiles repo and the bootstrap command.
9. **Verification checklist** — a list of reproducible checks that prove
   the host is ready: ssh works, `<SESSION_TOOL>` starts, service
   auto-restarts, etc.

**Fallback chains.** For each critical function, document a fallback.
Tool choices below are example fills; select tools per project in
`tokens.local.md`.

| Function         | Primary                   | Fallback                     |
|------------------|---------------------------|------------------------------|
| Remote access    | `<REMOTE_ACCESS_TOOL?>`   | direct SSH over public IP    |
| Power resilience | `<POWER_RESILIENCE_TOOL?>` | cron-triggered safe-shutdown |
| Git remote       | local `<PR_TOOL>`         | web UI                       |
| Model CLIs       | per `<FAMILY_CLI_MAP?>`   | fall back to web UI for authoring-only workers |

**Model-family CLI map.** The worker CLIs this host must support are
listed in `<FAMILY_CLI_MAP?>`. Example fill (replace per project):

```yaml
# Example only; fill per project in tokens.local.md
claude-opus:
  invocation: "claude --print --model claude-opus-4-6"
  capabilities: { shell: true, git: true, test_runner: true, doc_index: true }
codex:
  invocation: "codex --no-interactive"
  capabilities: { shell: true, git: true, test_runner: true, doc_index: true }
```

The template does not hardcode any specific model family, vendor, or CLI.
Infra tokens have example fills in `tokens.md`; those are examples, not
the framework's dependencies.

**Evidence.** Every verification-checklist item must include the command
used and the expected output.

**Output.** Write to `<ARTIFACT_OUTPUT_PATHS>`. Structure:

```markdown
---
id: infra-<CONTROL_PLANE_HOST>
role: infra-bootstrap
status: draft | applied | verified
---

# Infra Bootstrap — <CONTROL_PLANE_HOST>

## 1. OS system config
## 2. Network & remote access
## 3. Session resilience
## 4. Power resilience
## 5. Service supervision
## 6. Remote IDE / interactive access
## 7. Package baseline
## 8. Dotfiles
## 9. Verification checklist
| # | Check | Command | Expected | Result |
|---|-------|---------|----------|--------|
```

**Halt conditions.**

- You do not have privileged access to `<CONTROL_PLANE_HOST>` for steps that
  require it. Record what you attempted and halt; do not fake verification.
- A fallback is not available for a critical function. Record the gap and
  halt; the operator must decide whether to proceed without it.

## END INFRA BOOTSTRAP

## `<FINAL_REPORT_SCHEMA>`

The infra-bootstrap markdown above IS the final report.
