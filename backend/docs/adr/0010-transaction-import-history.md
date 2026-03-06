# ADR 0010: Transaction Import History With Error Downloads

## Status
Accepted

## Context
CSV import operations were operationally opaque after completion. Users needed traceability for import outcomes and downloadable row-level error context.

## Decision
- Add `transaction_imports` table to persist import metadata:
  - file name, status, row counts, duplicate/error counts, mapping, error rows
- Record entries for both preview and committed imports.
- Add APIs:
  - list import history per org
  - download error rows as CSV
- Add transactions UI panel to display import history and download errors.

## Consequences
- Pros:
  - better supportability and user trust in imports.
  - concrete audit trail for bulk financial changes.
- Cons:
  - additional storage for error row payloads.
