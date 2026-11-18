# A2B2 custom agents

Skills Manager deploys the skill into `.agents/skills/`. The [sync script](../scripts/sync_agents.py) installs its [four templates](../assets/codex-agents) into the target checkout's `.codex/agents/` before the first dispatch. To run it directly, pass the project root with `--project`.

The script copies missing profiles and upgrades files whose full contents match a released template. Matching current profiles are skipped. It preserves custom files and shows their differences, including same-role profiles stored under another filename. When releasing a changed template, add its SHA-256 digest to [the released profile list](../assets/codex-agents/known-versions.json) and retain the old digests. An unchanged copy of either release then remains eligible for a future update.

Codex resolves model and reasoning effort from the role file, explicit spawn arguments, `[agents]` defaults, then the parent. When an explicit or global model selection has no reasoning effort, Codex uses the model's default effort. Executor and ExpertAdvisor leave both settings to dispatch. Explorer and Reviewer pin both values. Service tier and sandbox policy follow the parent. Scope read-only assignments through the brief and role instructions.

## Verify a change

1. Parse the installed TOML and compare it with the matching template.
2. Check that the dispatch interface exposes the expected custom role and model controls. Use a fresh session if the host still shows the old profile.
3. For runtime verification, dispatch a bounded Sol implementation and a Terra screenshot acceptance through Executor. Use the child session records to confirm role, model and effort, then inspect the actual results.

[Codex custom-agent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents)
