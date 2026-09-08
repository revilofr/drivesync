# DriveSync Architecture

## Overview

DriveSync is a thin orchestration layer above `rclone`, providing a simple CLI for synchronizing multiple local directories with Google Drive.

**Core principle:** Never reimplement a feature already correctly provided by rclone.

## Architecture Diagram

```
                     DriveSync
                         │
         ┌───────────────┼──────────────┐
         │               │              │
       auth              dir          status
         │               │              │
         │        lightweight            │
         │        configuration          │
         │               │              │
         └───────────────┴──────────────┘
                         │
                       rclone
                         │
          ┌──────────────┼───────────────┐
          │              │               │
         OAuth          bisync          logs
          │              │               │
       (delegated)   (bidirectional)  (preserved)
                         │
                         ▼
                    Google Drive
```

## What DriveSync Does NOT Reimplement

- Google OAuth & token management (delegated to rclone)
- File comparison & synchronization (rclone bisync)
- Conflict resolution (rclone handles this)
- Lock management (rclone's internal mechanisms)
- Recovery logic (rclone bisync recovery)

## Core Components

### `cli.py`
- Command parsing and dispatch
- Text/JSON formatting
- User-facing output

### `config.py`
- Configuration file management
- Remote name and root path storage
- Configuration validation

### `directories.py`
- `dir add/remove/list` commands
- Parsing `~/.config/drivesync/directories.conf`
- Directory validation

### `rclone.py`
- Minimal wrapper around `rclone` binary
- Command construction
- Process execution & error handling
- Exit code capture

### `schedule.py`
- Crontab integration
- Local schedule persistence
- Drift detection (local config vs installed cron)
- Schedule status checking

### `run.py`
- `sync run` orchestration
- Execution logging
- Status tracking

### `auth.py`
- `auth setup/status/reconnect` commands
- rclone remote validation
- Authentication checking

### `sync_history.py`
- Execution logging (sync-history.jsonl format)
- State persistence
- Status reporting

## Configuration Layout

```
~/.config/drivesync/
├── config.ini              # General config (remote, root)
├── directories.conf        # Directory mappings (id=path)
└── schedules.json         # Scheduling configuration

~/.local/state/drivesync/
├── sync-history.jsonl     # Execution log (one JSON per line)
└── logs/
    ├── documents-2026-09-07_09-31-14.log
    └── projects-2026-09-07_09-35-20.log
```

## CLI Design

Command pattern: `drivesync <subject> <action>`

Stable verbs:
- Read/verify: `show`, `list`, `status`, `check`, `logs`
- Modify/execute: `add`, `remove`, `set`, `reset`, `run`, `install`, `uninstall`

**Key rule:** `run` never modifies configuration; `check` never modifies state.

## Authentication Model

1. DriveSync stores **only** the rclone remote name in config
2. All credentials/tokens remain managed by rclone
3. DriveSync delegates all OAuth operations to rclone
4. `auth setup` guides users through `rclone config`
5. `auth status` verifies remote is accessible

Example config:
```ini
[drive]
remote = gdrive-personal
root = DriveSync
```

## Directory Mapping Convention

With `remote = gdrive-personal` and `root = DriveSync`:

```
Local:  /home/user/Documents
        ↕
Remote: gdrive-personal:DriveSync/documents
```

The remote path is automatically derived from the directory ID (no manual config needed).

## Scheduling (V2+)

Current implementation uses system `cron`:
- `schedule set` updates local config only
- `schedule install` writes to actual user crontab
- `schedule uninstall` removes only DriveSync's cron block
- Drift detection warns if local config != installed cron

Future: Could migrate to `systemd --user` timers (architecture supports this).

## Offline & State Management

- Local files remain accessible offline
- No network = status `offline` (not `error`)
- Last sync timestamp always tracked
- Distinguish `last_attempt` vs `last_success`
- State persisted atomically (write temp file, rename)

## Status Codes

| Code | Status    | Meaning |
|---:|-----------|---------|
| 0 | success | Last sync succeeded |
| 1 | offline | Network unreachable |
| 2 | error | rclone or config error |
| 3 | never_run | No sync attempted yet |
| 4 | running | Sync in progress |

## Logging Philosophy

- Preserve all rclone logs (source of truth)
- Store path to last log in state
- Add minimal DriveSync header/footer for context
- One log file per execution per directory

## Typical Workflow

```bash
# Initial setup
drivesync auth setup
drivesync auth status

# Add directory
drivesync dir add documents ~/Documents

# Verify access
drivesync sync check documents

# First sync (may need --resync)
drivesync sync run documents --resync

# Regular sync
drivesync sync run documents

# Check status
drivesync status documents

# View logs
drivesync logs documents
```

## Design Priorities (in order)

1. **No data loss** — ever
2. **Clear behavior** — users understand what's happening
3. **Simplicity** — minimal code, max reuse of rclone
4. **Maximum rclone usage** — don't duplicate features
5. **Offline support** — local files remain usable
6. **Observability** — clear status and logs
7. **Scriptability** — predictable output and exit codes
8. **Maintainability** — small, focused modules

## What DriveSync Will NOT Become

- A new Google Drive client
- An OAuth implementation
- A filesystem mount layer
- A custom conflict resolver
- A persistent daemon (uses cron)
- A database-backed tool
- An overly complex task framework

DriveSync is intentionally a thin orchestration layer.

## Python Implementation

- **Minimum version:** Python 3.10+
- **Dependencies:** Standard library only (MVP)
- **Code layout:** Small, focused modules
- **No external packages:** Keeps installation simple

## Decision Rule During Development

Before implementing any feature:

> Does rclone already do this?

If yes → use rclone  
If no → consider if DriveSync really needs it

Add to DriveSync only what improves ergonomics, orchestration, status reporting, or scriptability.
