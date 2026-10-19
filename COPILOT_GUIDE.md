# DevCircuit Lifecycle Copilot

The copilot is a conversational facilitation layer over the authoritative DevCircuit control plane. It records human dialogue, explains lifecycle state and evidence, prepares bounded mandates and exact decision packets, and resumes authorized workflows. Conversation is never authority.

## Authority protocol

1. Open an expiring session for an existing human principal.
2. Converse through `say`; every message is signed and explicitly non-authoritative.
3. Prepare a mandate or active-scope authorization decision.
4. Inspect the decision packet, evidence, required principal, payload digest, and exact challenge.
5. Approve or reject using the exact challenge. Ambiguous phrases have no effect.
6. The control plane independently validates the principal, role, scope, lifecycle state, and non-replay status before applying an effect.

Opening a low-level session proves possession of the locally protected principal key. The DevCircuit `devcircuit` interface stores local bearer sessions in a mode-0600 internal vault and never displays their tokens. This reference mechanism demonstrates correct interaction semantics but is not production authentication; connect the same decision API to organizational identity, MFA, and externally managed signing keys before production use.

Most people should use `devcircuit-operator`, which presents these controls as one guided journey and groups actionable requests for review. `devcircuit-copilot` remains the lower-level facilitation interface.

## Commands

```sh
devcircuit-copilot --root ./my-system session-open --principal engineering-reviewer --credential-file ./my-system/.devcircuit/keys/engineering-reviewer.key
devcircuit-copilot --root ./my-system status
devcircuit-copilot --root ./my-system facilitator-register --session OWNER_SESSION --token OWNER_TOKEN --name codex --kind codex
devcircuit-copilot --root ./my-system say --session SESSION --token TOKEN --message "What is next?"
devcircuit-copilot --root ./my-system say --session SESSION --token TOKEN --facilitator codex --message "Explain the current evidence and next gate"
devcircuit-copilot --root ./my-system mandate-propose --session SESSION --token TOKEN --file mandate.json
devcircuit-copilot --root ./my-system authorization-propose --session SESSION --token TOKEN --scope 'build:DIGEST'
devcircuit-copilot --root ./my-system specification-propose --session SESSION --token TOKEN --change-id CHANGE --file next-spec.json
devcircuit-copilot --root ./my-system specification-apply --session SESSION --token TOKEN --change-id CHANGE
devcircuit-copilot --root ./my-system decide --session SESSION --token TOKEN --decision-id ID --outcome approve --confirmation 'APPROVE ID PROPOSAL_DIGEST'
devcircuit-copilot --root ./my-system resume --session SESSION --token TOKEN --run-id RUN
```

`mandate.json` has the exact fields `run_id`, `objective`, `driver`, `allowed_paths`, `requirements`, `max_iterations`, `max_changes`, `max_bytes`, and `expires_at`.

## Separation of duties

- The copilot may explain and propose.
- The engineering agent may make bounded source and test proposals.
- The engineering reviewer may authorize a mandate or exact build scope.
- The release owner may accept a specification or artifact and authorize deployment.
- DevCircuit validates state and applies effects.
- Neither conversational text nor an agent response can impersonate a human decision.

Every session, message, proposal, human decision, effect, and resumed run is written into the signed, hash-chained lifecycle record.
