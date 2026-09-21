# Safe examples and private runtime data

This is a public repository. Skills, prompts, templates, fixtures, and workflow
sketches must be reusable without disclosing a person's or customer's data.

- Use fictional people and reserved example domains (`example.com` or `.example`).
  Use reserved fictional phone numbers, such as `+1 202-555-0100`. Leave profile
  links blank unless a parser fixture specifically requires their shape; those
  fixtures must stay offline and must not be fetched or enriched.
- Keep guest lists, research dossiers, contact exports, call transcripts,
  screenshots, customer run results, and hashed contact identifiers outside this
  repository. Private working copies can use the ignored `.private/` directory.
- Store API keys, browser cookies, OAuth tokens, signing secrets, and webhook
  credentials in a secret store or private environment configuration. Placeholder
  references in a sketch are not instructions to paste secrets into tracked JSON.
- Supply workspace, table, list, channel, and deployment identifiers at runtime
  or in private deployment configuration. Generic examples should not identify
  an actual customer's workspace or run.
- Do not commit local absolute paths containing a person's username. Prefer
  caller-provided paths or paths relative to the current user's home directory.

Before sharing a change, inspect its complete diff and sample data, then scan
both the current files and Git history with a credential scanner such as
Gitleaks. Automated scans do not replace reviewing names, private links, account
identifiers, customer examples, and generated artifacts. The ignore rules help
with new files; they do not protect files that Git already tracks.

If a live credential is exposed, revoke or rotate it through the provider and
remove it from current content. Editing a file does not erase earlier commits,
forks, caches, or copies. Coordinate any necessary history cleanup with the
repository owner; do not put the exposed value in a public issue or pull request.

The `drafts/` package is experimental. Its workflow sketches require private
configuration, implementation, and testing before deployment.
