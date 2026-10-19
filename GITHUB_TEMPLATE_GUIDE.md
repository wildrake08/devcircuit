# GitHub “Use this template” guide

Use `devcircuit` as the canonical kernel/distribution repository name and `devcircuit-starter` as the canonical GitHub template repository name. Publish the contents of `github-template/`, not the `devcircuit` kernel repository, as the `devcircuit-starter` repository root. The thin starter contains only a marker, a short application-facing README, safe ignore rules, and a bootstrap check workflow.

After selecting **Use this template**, clone the new repository and initialize it in place:

```sh
uvx --from devcircuit devcircuit --root . create YOUR-APPLICATION \
  --purpose "YOUR PURPOSE" \
  --beneficiary "YOUR BENEFICIARY"
```

Initialization verifies the thin-starter marker and rejects unexpected top-level content. It then creates the application source, application tests, application README, GitHub quality workflow, and hidden `.devcircuit/` state. The marker is removed. Kernel code and release evidence remain in the independently versioned `devcircuit` distribution.

Start the primary interface:

```sh
devcircuit --root . chat
```

Production repositories should configure GitHub rulesets, CODEOWNERS, organizational identity, MFA, protected environments, and real deployment/evidence adapters. These controls cannot be transferred by a template copy.

Kernel updates are dependency updates. Do not overlay the kernel repository onto an application. CLSES v4 and v5 projects use the previewable `devcircuit migrate` operation described in `MIGRATION_TO_DEVCIRCUIT.md`.
