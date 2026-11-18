# A2B2 custom agents

The local source of the skill holds four templates in [assets/codex-agents](../assets/codex-agents). Copy the corresponding files to the A2B2 checkout's `.codex/agents/` after comparing them with its existing profiles. Skills Manager deploys the skill files into `.agents/skills/`. Codex loads the role files from `.codex/agents/`.

Codex resolves model and reasoning effort from the role file, explicit spawn arguments, `[agents]` defaults, then the parent. When an explicit or global model selection has no reasoning effort, Codex uses the model's default effort. Executor and ExpertAdvisor leave both settings to dispatch. Explorer and Reviewer pin both values. Service tier and sandbox policy follow the parent. Scope read-only assignments through the brief and role instructions.

## Verify a change

1. Parse the installed TOML and compare it with the matching template.
2. Check that the dispatch interface exposes the expected custom role and model controls. Use a fresh session if the host still shows the old profile.
3. For runtime verification, dispatch a bounded Sol implementation and a Terra screenshot acceptance through Executor. Use the child session records to confirm role, model and effort, then inspect the actual results.

[Codex custom-agent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents)
