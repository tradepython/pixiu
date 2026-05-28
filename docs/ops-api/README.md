# Pixiu Ops API v1

Pixiu Ops API is the HTTP contract used by `pixiu ops` to inspect, replay,
optimize, and safely operate strategy instances that are already running on a
remote platform.

The API is intentionally provider-neutral. A server can be OEOEHui, another
trading platform, or a local replay service. Provider-specific identifiers such
as `logger_uid`, `ea_settings_uid`, database scopes, or WebSocket login tickets
must be hidden behind a stable `strategy_id`.

## Scope

This protocol is for online strategy operations:

- discover server capabilities
- authenticate a user token
- list strategy instances
- fetch a strategy snapshot
- fetch logs
- inspect command queues and command results
- inspect and evaluate risk rules
- export a replay package
- exchange optimization reports
- query and update guard state
- query, validate, apply, and rollback settings

This protocol is not a live trading runtime. It does not define market data
subscriptions, broker order execution, or terminal command polling. Those remain
the responsibility of `pixiu live` or the provider's existing execution layer.

## Authentication

Clients use a user or service token:

```http
Authorization: Bearer <token>
```

The token identifies the caller. The server must perform authorization for every
strategy resource. Clients must not send provider-internal user identifiers as
trusted input.

Servers should support scoped tokens:

- `ops:read`
- `ops:replay:export`
- `ops:guard:write`
- `ops:settings:write`

Write operations must be audited by the provider.

## Commands And Risk Rules

Providers should expose command history and risk decisions separately from EA
logs. This lets `pixiu ops` distinguish between:

- the strategy not generating an order
- an order command waiting in the provider queue
- an order command dispatched to an executor
- an order command blocked by guard or platform risk rules
- an order command executed and reported back

Risk rules describe configured limits, while risk evaluation answers whether a
candidate action would be allowed at the current moment.

## Resource Model

`strategy_id` is the only required strategy locator in Pixiu Ops API.

For OEOEHui, a provider may map it internally to:

```text
logger_uid + ea_settings_uid + symbol
```

Other providers may map it to any stable strategy instance identifier.

## Guard Modes

The first protocol version defines three guard modes:

- `normal`: the strategy may create new orders according to provider policy.
- `pause_open`: new open-order commands are blocked, while existing-position
  management may continue.
- `observe`: no trading commands should be accepted from the strategy; the
  provider may still collect telemetry and runtime state.

Providers may support fewer modes and must advertise support in
`GET /v1/capabilities`.

## Replay Package

Replay export returns a `pixiu.replay.v1` package. It is designed to be converted
to a local Pixiu tester scenario without exposing provider internals.

The package includes:

- account snapshot
- symbol metadata
- price rows
- initial orders
- runtime data
- script settings
- account time series
- risk events
- optional logs and command history

## Optimization Report

Optimization runs produce a `pixiu.optimization.report.v1` document. The report
contains a baseline case, tested cases, risk metrics, risk events, ranking, and
an optional recommended case. A settings proposal may reference a report case
through `source.type=optimize` and `source.case_id`.

## OpenAPI

The first OpenAPI draft lives in:

```text
openapi/pixiu-ops-v1.yaml
```

Shared schemas live in:

```text
schemas/*.json
```

## MVP Client Commands

The protocol is intended to support these commands first:

```bash
pixiu ops context use prod
pixiu ops auth whoami
pixiu ops get strategies
pixiu ops get snapshot <strategy_id>
pixiu ops logs <strategy_id> --since 2h
pixiu ops commands list <strategy_id> --since 2h
pixiu ops risk rules <strategy_id>
pixiu ops risk eval <strategy_id> --action open_order
pixiu ops export replay <strategy_id> --since 4h -o replay.json
pixiu ops optimize replay.json -o optimize-report.json
pixiu ops guard pause-open <strategy_id> --reason "debug"
pixiu ops guard resume <strategy_id> --reason "verified"
pixiu ops settings diff <strategy_id> --file params.yaml
pixiu ops settings apply <strategy_id> --file proposal.json --dry-run
```
