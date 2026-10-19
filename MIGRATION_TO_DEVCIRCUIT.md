# Migrating CLSES projects to DevCircuit 1.0

Preview the migration:

```sh
devcircuit --root . migrate
```

For external-kernel CLSES v5 projects, the plan moves `.clses/` state without changing application files. For embedded CLSES v4 projects, it inventories framework files against the signed legacy template manifest. Modified framework files are preserved as conflicts and block automatic application. Source, tests, Git history, CODEOWNERS, the signed ledger, authorizations, unresolved decisions, and application snapshots remain in place.

After reviewing the exact plan:

```sh
devcircuit --root . migrate --apply
```

Application moves are recoverable: `.clses/` or `.clses-v1/` is copied to `.devcircuit-migration-backup` before it is moved to `.devcircuit/`. Only manifest-matching CLSES v4 framework files are removed. Kernel upgrades thereafter use the external `devcircuit` dependency instead of overlaying framework source onto the application.
