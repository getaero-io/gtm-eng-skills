# Contributing to GTM Eng Skills

## Skill structure

Each skill lives in its own directory:

```
skills/<skill-name>/
└── SKILL.md
```

`SKILL.md` must have YAML frontmatter:

```yaml
---
name: skill-name
description: |
  One paragraph explaining what this skill does and when it triggers.

  Triggers:
  - "example user request that activates this skill"

  Requires: Deepline CLI — https://code.deepline.com
---
```

## Skill quality checklist

- [ ] Focused on exactly one GTM workflow
- [ ] Includes a working `deepline enrich` or `deepline tools execute` example
- [ ] Includes a `--rows 0:1` pilot step before any full run
- [ ] Documents required and optional input columns
- [ ] Links to code.deepline.com for setup
- [ ] Written for external audience (no internal file paths or implementation details)

## Submitting a PR

1. Fork the repo
2. Create a branch: `git checkout -b feat/skill-name`
3. Add your skill in `skills/<name>/SKILL.md`
4. Add it to `.claude-plugin/marketplace.json` skills array
5. Update the skills table in README.md
6. Open a PR with a clear description of what the skill does
