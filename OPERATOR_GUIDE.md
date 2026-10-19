# DevCircuit Guided Operator

The primary interface is `devcircuit`; it hides session tokens, exact confirmation strings, mandate files, and automatic continuation. `devcircuit-operator` remains the advanced deterministic interface documented below for diagnostics, compatibility, and integration testing.

Version 4.5 adds the same journey as a loopback visual interface plus onboarding-template and environment-discovery commands. See `ONBOARDING_AND_VISUAL_OPERATOR.md`. The command and visual surfaces delegate to this operator; neither has independent authority.

`devcircuit-operator` is the thin human-facing layer over intake, the lifecycle copilot, autonomous execution, and the authoritative control plane. It presents one journey and one status view while leaving the underlying controls intact.

## Upgrade an initialized template safely

Overlay the released immutable template files while preserving `.git`, `.devcircuit`, `.github/CODEOWNERS`, `src`, and `tests`. Authenticate as `release-owner`, then prepare the exact transition:

```sh
devcircuit-operator --root . template-upgrade \
  --session "$RELEASE_SESSION" \
  --token "$RELEASE_TOKEN"
```

Review the old and new manifest digests, prior baseline record, preserved snapshot digest, and customizations. Apply the returned one-time challenge with `devcircuit-operator decide`. Approval rebinds the template baseline, preserves pending application differences, and moves active runs to `changes_requested`; it does not accept source, tests, artifacts, or deployment. Prepare a new engineering mandate for the reassessment.

## The seven-step journey

1. Understand the need.
2. Authorize the exact product baseline.
3. Authorize bounded engineering.
4. Engineer and verify.
5. Authorize the exact build.
6. Accept the artifact and authorize deployment.
7. Operate, measure outcomes, and reassess changes.

At every point `status` returns a headline, current step, progress, one recommended next action, open intake questions, actionable authority requests, a plain evidence summary, and the authority notice. The primary interface suppresses technical digests; advanced operations retain them for traceability.

## Begin in an empty repository

```sh
devcircuit-operator --root ./coffee-pos setup \
  --system-id coffee-pos \
  --purpose "Operate a coffee cart point of sale" \
  --beneficiary "coffee-cart operator"

devcircuit-operator --root ./coffee-pos begin --profile point-of-sale
devcircuit-operator --root ./coffee-pos status
```

`begin` applies the minimum-question intake policy. For an empty point-of-sale context, the result contains five consolidated question groups. Supply answers as one JSON object:

```sh
devcircuit-operator --root ./coffee-pos answer --file intake-answers.json
```

The resulting minimum viable baseline remains `proposed_not_authorized`. An authenticated `owner` must use `authorizations` and the exact decision challenge to authorize that digest-bound product baseline. The packet displays the full baseline, not only its digest. Approval binds its product purpose, beneficiaries, outcome criterion, and operating conditions into the active executable specification. Mandate preparation fails closed until both authorization and exact binding exist. Product-baseline authorization does not authorize engineering, release, or deployment.

## Authenticate and prepare work

```sh
devcircuit-operator --root ./coffee-pos session-open \
  --principal engineering-reviewer \
  --credential-file ./coffee-pos/.devcircuit/keys/engineering-reviewer.key

devcircuit-operator --root ./coffee-pos mandate \
  --session SESSION --token TOKEN --file mandate.json
```

The mandate response contains an exact approval and rejection challenge. The reviewer uses `decide`; ordinary conversation has no effect:

```sh
devcircuit-operator --root ./coffee-pos decide \
  --session SESSION --token TOKEN \
  --decision-id DECISION \
  --outcome approve \
  --confirmation 'APPROVE DECISION PROPOSAL_DIGEST'

devcircuit-operator --root ./coffee-pos continue \
  --session SESSION --token TOKEN --run-id RUN
```

An owner registers the chosen execution agent once through the same surface with `driver-register`. `--kind codex` uses the built-in adapter; `--kind generic` accepts a JSON argument array containing `{prompt}`.

Reject decisions with `--reason "..."`. Rejection is enforced: the unchanged scope cannot later be approved, and an affected engineering run returns to revision with the rationale in its agent context. End an exposed bearer session immediately with `session-close`. Revoke an active engineering mandate with `mandate-revoke`, a nonempty reason, and the exact `REVOKE RUN_ID MANDATE_DIGEST` confirmation; use a new run identity for any superseding mandate.

## Consolidated authorization review

When the run reaches an authority boundary:

```sh
devcircuit-operator --root ./coffee-pos authorizations \
  --session SESSION --token TOKEN
```

The command creates one review packet for the authenticated principal. The owner receives the baseline decision and the engineering reviewer receives the build decision with bounded trial evidence. Artifact acceptance and deployment are now durable sequential stages: deployment cannot be authorized until acceptance has been recorded. Each decision retains its own scope, evidence, exact challenge, role check, and replay protection.

When execution establishes an architecture and implementation language, the operator marks the corresponding safe defaults as replaced by execution evidence and removes them from the deferred list. The authorized product-intent fields remain immutable. After closure, progress is seven of seven and the status reads “Cycle closed; continuous monitoring and change-triggered reassessment are active.” Monitoring is ongoing, not an unfinished authorization step.

Preparing or reading a packet grants nothing. Every item must be explicitly decided. A packet cannot include a decision assigned to another principal, and repeated preparation reuses an existing unresolved proposal instead of creating duplicate requests.

## Conversational turns

The deterministic `turn` operation supports `status`, `begin intake`, `answer intake`, `reassess intake`, and `prepare authorizations`. Structured data is supplied through `--data-file`. The `reassess` command provides the same change-triggered reopening without a conversation. Ambiguous language is read-only. Statements such as “I approve” are explicitly rejected as authority and direct the person to the exact decision challenge.

```sh
devcircuit-operator --root ./coffee-pos turn \
  --session SESSION --token TOKEN --message "status"
```

An optional external LLM facilitator may still be connected through `devcircuit-copilot`. It can explain the guided view, but it cannot change routing, create arbitrary scopes, authenticate a human, or approve a decision.

## Production boundary

The reference operator uses local credential possession, bearer session tokens, a command-line JSON view, a local simulated deployment, and deterministic phrase routing. A production user interface should render the same operator contract, connect decisions to organizational identity and MFA, protect tokens and signing keys, and supply authentic target-environment evidence adapters. The thin layer does not convert the reference demonstration into universal production certification.
