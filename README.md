# DevCircuit 1.0

DevCircuit is a complete end-to-end, closed-loop software engineering system. Developers describe what the software must achieve; autonomous execution services specify, implement, verify, deploy, and reassess it within bounded mandates; authenticated humans retain consequential authority.

**Describe it. Govern it. Ship it. Keep it working.**

DevCircuit separates the authority and assurance kernel from generated applications. This repository contains the kernel, operator, profiles, adapters, normative schemas, and independent release evidence. The `github-template/` directory is the intentionally thin application starter.

## Create a system

```sh
devcircuit --root ./coffee-cart create coffee-cart \
  --purpose "Operate a safe, reliable coffee-cart point of sale" \
  --beneficiary "coffee-cart operators and customers" \
  --profile point-of-sale

cd coffee-cart
devcircuit chat
```

The generated repository is application-specific. It contains application source, application tests, GitHub automation, an application README, and hidden `.devcircuit/` lifecycle state. It does not contain `devcircuit`, kernel tests, release assessments, or DevCircuit framework documentation. The local reference opens and renews its protected local sessions internally when the conversation reaches a review boundary.

## Normal interaction

Inside `devcircuit chat`, describe a slice such as:

> Add a product catalog, cart quantities, integer-cent totals, completed transactions, and rejection of raw card data.

DevCircuit performs intake, prepares the exact baseline, creates a bounded agent mandate, runs the configured agent, evaluates changes, repeats tests, builds the artifact, and advances to the next real boundary. The human reviews plain-language evidence and uses `approve next` or `reject next: reason`. Tokens, digests, challenges, mandate files, and run identifiers remain internal.

## Lifecycle states

```text
intent proposed
→ product baseline authorized
→ bounded engineering authorized
→ engineered and tested
→ exact build authorized
→ artifact accepted
→ deployment authorized
→ deployed
→ monitoring active
→ sustained production evidence verified
→ cycle closed
```

Deployment and closure are deliberately separate. Unsupported outcomes leave the system safely deployed and monitoring; they cannot be converted into a closure claim by generic health checks.

## Interfaces

- `devcircuit`: primary application-centered conversation and orchestration
- `devcircuit-operator`: advanced deterministic lifecycle operations
- `devcircuit-control`: low-level control-plane diagnostics and integration
- `devcircuit-production-verify`: independent production-evidence verification

## Existing projects

Use `devcircuit migrate` to preview migration from CLSES v4 or v5. `devcircuit migrate --apply` preserves Git history, source, tests, ledger continuity, and unresolved application state while moving lifecycle data to `.devcircuit/`. See `MIGRATION_TO_DEVCIRCUIT.md`.

## Assurance boundary

DevCircuit enforces intrinsic conformance, cross-artifact relations, explicit authority, authentic build evidence, and production-evidence gates. A package release demonstrates the framework against controlled systems. It does not certify every generated application or production environment. Production adequacy requires current signed evidence from the declared target environment and expires with that evidence.

See `DEVELOPER_EXPERIENCE.md`, `NORMATIVE.md`, `PRODUCTION_PROFILE.md`, and `CONFORMANCE_REPORT_1.0.0.md`.
