# DevCircuit 1.0 developer experience

DevCircuit treats the application as the product and its authority and assurance kernel as an external, versioned dependency.

## Create and converse

```sh
devcircuit --root ./coffee-cart create coffee-cart --profile point-of-sale
cd coffee-cart
devcircuit chat
```

Creation performs secret-safe environment discovery, installs an application-specific scaffold, initializes hidden lifecycle state, and begins minimal-viability intake. The generated repository does not contain the DevCircuit implementation, kernel tests, conformance reports, or release machinery.

In the conversation, answer one material intake question at a time in ordinary language, then describe the desired slice. DevCircuit prepares the product baseline and bounded engineering work, invokes the configured coding agent, runs tests, builds the exact artifact, and advances automatically until it reaches a human authority or authentic-evidence boundary.

`approve next` and `reject next: reason` are explicit authenticated decisions when exactly one review is pending. Conversation that merely sounds approving has no effect.

## Authority and simplicity

The local reference profile keeps bearer tokens in a mode-0600 internal session vault. Ordinary users do not copy session tokens, proposal digests, exact challenge strings, mandate JSON, or run identifiers. Production deployments must replace local credentials with an organizational identity adapter and MFA.

The normal lifecycle is durable: built, accepted, deployment authorized, deployed, monitoring active, outcome evidence sufficient, and closed. Deployment never implies that the product outcome was achieved.
