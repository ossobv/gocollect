# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands

All commands are run from `gocollect-client/`:

```bash
make                  # Build the gocollect binary (statically linked)
make check            # Run tests + gofmt + golint + go vet
make pretty           # Format code with gofmt and run linting
make clean            # Remove build artifacts
make testrun          # Run with test config (requires sudo)
make install          # Full install (binary, collectors, init scripts)
make tgz              # Create distributable tarball
```

Run a single Go test:
```bash
cd gocollect-client && go test ./... -run TestName
```

The binary is compiled with static linking (`-tags netgo`) and has the version string embedded via `-ldflags "-X main.versionStr=$(VERSION)"`. Version is detected from `debian/changelog` first, then `git describe`.

## Architecture Overview

GoCollect is a system inventory daemon that periodically collects server metadata and POSTs it as JSON to a central server.

### Core Data Flow

```
gocollect.go (main)
  └─ runner.Run()
       ├─ httpInit() — setup HTTP client (45s timeout)
       ├─ setCoreIDData() — run "core.id" collector first (provides hostname, IP, regid)
       ├─ needsRegister() → runRegister() — POST core.id data to register_url
       ├─ runAll() — execute all collectors, POST each result to push_url
       └─ loop: sleep 4h on success, exponential backoff (5m → 4h) on failure
```

### Package Structure

- **`runner/`** — Core execution engine
  - `runner.go` — public API (`Run()`, `Get()`)
  - `internal.go` — registration, collector execution, `runInfo` struct
  - `http.go` — HTTP POST, JSON communication with server

- **`data/`** — Data representation
  - `collectors.go` — collector registry and interface definitions
  - `collected.go` — JSON data wrapper with `GetString`/`BuildString`/`SetString` helpers; implements `io.Reader` for HTTP streaming

- **`shcollectors/`** — Shell script discovery and execution
  - Scans configured `collectors_path` entries, executes each as `timeout 180s <script>` with a clean environment
  - Last path wins for duplicate collector names (allows overrides)
  - Errors returned as `{"error":"EINVAL"}`

- **`collectors/`** — Built-in Go collectors
  - `core.foo/` — example/template builtin
  - `core.meta/` — reads YAML files for custom metadata
  - 28 shell script collectors: `core.*`, `os.*` (distro, kernel, memory, network, pkg, storage, uptime), `sys.*` (cpu, firmware, ipmi, storage, security), `app.*` (docker, k8s, containerd, lldp, etc.)

- **`signal/`** — OS signal handling (SIGALRM wakes sleep, SIGHUP/SIGUSR1 trigger early rescan)

### Collector Execution Order

`core.id` always runs first — its output (hostname, IP, `regid`) is embedded in every HTTP request to the push server. Other collectors are sorted alphabetically within their category (`core.*` → `sys.*` → `os.*` → `app.*`).

### Configuration

Config files use `key = value` syntax with `include = /path` for composition (no globbing). Key settings:
- `api_key` — optional auth key
- `register_url` — server endpoint for first-time registration
- `push_url` — data POST endpoint (supports `{regid}` and `{_collector}` placeholders)
- `collectors_path` — one or more paths scanned for collector executables (last wins)

### Backend Servers (Python, in `servers/`)

Four Python consumers process the collected data:
- **`rmq2file/`** — RabbitMQ → flat files
- **`rmq2es/`** — RabbitMQ → Elasticsearch
- **`rmq2nb/`** — RabbitMQ → Netbox (IPAM/DCIM; most complex, supports dry-run)
- **`wsgi2file/`** — HTTP/WSGI → flat files (simpler alternative without RabbitMQ)

Shared Python utilities live in `servers/lib/` (RabbitMQ helpers, HTTP utilities, logging).
