Use `ai_inference` for plain text or structured-output model calls with no tool use.

Use `deeplineagent` when the task benefits from streaming output and tool use across the current whitelist: `exa_search`, `exa_answer`, `google_search`, `parallel_search`, and `bash`.

For research tasks, prefer an adaptive loop: cheap parallel search first, synthesize, then only run targeted follow-up or primary-source reads if key gaps remain.

Use `exa_answer` for direct citation-backed answers after retrieval. Do not rely on `exa_contents` inside `deeplineagent`.

When `bash` is enabled, `/refs/prompts.json` is available as a lazily loaded reference file for GTM prompt-template lookup.

Prefer Deepline-native tools over freeform bash when structured provider actions already exist.
