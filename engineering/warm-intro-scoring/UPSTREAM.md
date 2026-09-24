# Source and maintenance

Originally maintained in `getaero-io/gtm-eng-skills/engineering/warm-intro-scoring`. Refreshed from the reviewed `getaero-io/deepline-api` embedded recipe at commit `d9a2a73003`.
The source includes MIT-licensed reference code, preserved in `LICENSE` and pinned by `vendor-manifest.json`.

The upstream CLI distribution adds a router recipe. This permanent engineering copy contains the execution guide, installation/test guide, a fictional smoke test, an intro-draft template and a reproducible archive command. It also includes the tested `coverage.notes` renderer change and its regression test from the source worktree. No personal export, production run receipt, source credential or real-person artifact is bundled.

Maintain this copy through reviewed PRs; do not fetch a moving branch at runtime. After changes, run `python3 plays/check_all.py`, the demo, and archive/extract tests. Refresh `package-manifest.json` SHA-256 values only for reviewed source changes. It lists every shipped source except itself; the packager does not discover files dynamically. Keep caches, local outputs and user data out of the manifest.

Imported TypeScript keeps its runtime-validated JSON contract types with local lint annotations; standalone browser harnesses remain CommonJS. The immutable vendor files are unchanged.
