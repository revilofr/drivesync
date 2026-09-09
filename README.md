# DriveSync

DriveSync is a lightweight Linux CLI that orchestrates `rclone` for simple synchronization of local directories.

## Why DriveSync?

Google Drive does not provide an official desktop synchronization client for Linux.

`rclone` fills this gap, especially with `bisync`, but daily usage remains quite technical: configuring remotes, managing paths, automation, logs, resynchronization, and precautions for sensitive operations.

DriveSync provides a simple layer above `rclone` to manage these synchronizations more easily.

### What DriveSync brings

- persistent configuration of local ↔ remote folders ;
- simplified launch of synchronizations ;
- automation and scheduling ;
- checking statuses, histories, and logs ;
- optional GNOME Executor integration to display synchronization health directly in the system bar ;
- safeguards for sensitive operations like `bisync --resync` ;
- centralized management of multiple synchronizations.

The goal is simple:

> **Configure `rclone` once, then use DriveSync daily.**

DriveSync does not reimplement the synchronization engine: it deliberately relies on `rclone`, a mature open source project distributed under the MIT license.

```
DriveSync
    │
    ▼
rclone bisync
    │
    ▼
Google Drive
```

Initial Google Drive configuration remains necessary, in particular the creation of OAuth credentials and the `rclone` remote.

Dedicated documentation is available in [`DRIVESYNC_GOOGLE_AUTH.md`](DRIVESYNC_GOOGLE_AUTH.md).

### Dependency on rclone

DriveSync uses [`rclone`](https://rclone.org/) as its synchronization engine.

`rclone` is an independent project distributed under the MIT license.

DriveSync is neither affiliated with nor officially endorsed by the rclone project or Google.

## Current project status

Current state of the project:

- configuration storage
- registration of managed directories
- listing and deletion of registered directories

The synchronization engine is intentionally delegated to `rclone`.

Getting started documentation is in [GETTING_STARTED.md](GETTING_STARTED.md).
Detailed Google Drive OAuth documentation is in [DRIVESYNC_GOOGLE_AUTH.md](DRIVESYNC_GOOGLE_AUTH.md).

## Project

DriveSync was created by `revilofr`, with the help of Claude.

The project is open source and everyone is welcome to use it, clone it, improve it, and adapt it to their needs.

## Quick start

From the project root:

```bash
PYTHONPATH=. python3 -m drivesync dir list
```

Short `drivesync` command (without `python3 -m`) on Ubuntu 24:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Then verify:

```bash
drivesync --help
```

Option to avoid activating the environment each session:

```bash
echo "alias drivesync='/path/to/drivesync/.venv/bin/drivesync'" >> ~/.bashrc
source ~/.bashrc
drivesync --help
```

Enable Bash autocompletion:

```bash
source /path/to/drivesync/completion.bash
```

Enable Zsh autocompletion:

```zsh
source /path/to/drivesync/completion.zsh
```

Persistent Bash activation:

```bash
echo "source /path/to/drivesync/completion.bash" >> ~/.bashrc
source ~/.bashrc
```

Persistent Zsh activation:

```zsh
echo "source /path/to/drivesync/completion.zsh" >> ~/.zshrc
source ~/.zshrc
```

## Tests

Run the test suite:

```bash
python3 -m unittest discover -s tests
```

## Prerequisites

- Linux
- Python 3.10 or later
- no external Python applicative dependencies for the current MVP
- `rclone` is required for `auth`, `sync check`, and `sync run`, but not for `dir add/remove/list/show`
- `cron` is required for `schedule install` and `schedule uninstall`

## Dependencies

Runtime dependencies (current state):

- Python 3.10+
- Python standard library only

Tool dependencies (development / local installation):

- `pip`
- `setuptools`

System dependencies:

- Linux
- `rclone` (required for `auth`, `sync check`, and `sync run`)
- `cron` (required for `schedule install` and `schedule uninstall`)
- `rsync` is not a dependency

Recommended `rclone` version for DriveSync:

- reasonable minimum: `>= 1.66`
- recommended: `>= 1.71`
- ideally: a recent stable version

Check if `rclone` is installed:

```bash
command -v rclone
```

Also verify its version:

```bash
rclone version
```

## End-to-end walkthrough

This walks through a full setup, from a clean machine to an automatically
synchronized folder, in a few steps.

1. **Install DriveSync** (see [Quick start](#quick-start) above):

   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -e .
   drivesync --help
   ```

2. **Configure Google Drive authentication.** DriveSync relies on an
   `rclone` remote; the full OAuth setup (Google Cloud credentials, remote
   creation, validation) is documented step by step in
   [DRIVESYNC_GOOGLE_AUTH.md](DRIVESYNC_GOOGLE_AUTH.md). Once your remote
   exists, register it with DriveSync:

   ```bash
   drivesync auth setup gdrive
   ```

3. **Watch a local folder** by mapping it to a remote path:

   ```bash
   drivesync dir add documents ~/Documents --remote-dir perso/documents
   ```

4. **Run a first synchronization** to validate the mapping before
   automating anything:

   ```bash
   drivesync sync run documents
   ```

5. **Set the synchronization frequency**, then apply it to the system
   scheduler:

   ```bash
   drivesync schedule set documents --frequency 5minutes
   drivesync schedule install
   ```

   `schedule set` only updates DriveSync's local configuration; `schedule
   install` is what actually writes the cron entry. Re-run `schedule
   install` any time you change the frequency.

6. **Check status and history** at any time:

   ```bash
   drivesync status
   drivesync sync logs documents
   ```

At this point, `documents` is synchronized automatically in the background
on the configured schedule, with a local history you can inspect.

### Going further: a visual indicator in the GNOME top bar

If you want to see synchronization health at a glance instead of running
`status` manually, DriveSync ships a compact indicator for the GNOME
Executor extension:

```bash
drivesync status --executor
```

Add it as an active command in Executor (see the [Example with GNOME
Executor](#example-with-gnome-executor) section below). If you use other
hardware/status scripts the same way, check out
[revilofr-executors](https://github.com/revilofr/revilofr-executors), a
companion collection of small Executor scripts (battery levels, etc.) by
the same author.

## Documentation

See [GETTING_STARTED.md](GETTING_STARTED.md) for:

- local installation
- `rclone` installation procedure (without uninstallation)
- launch commands
- tests
- configuration storage
- `rclone` installation on Ubuntu

See [DRIVESYNC_GOOGLE_AUTH.md](DRIVESYNC_GOOGLE_AUTH.md) for:

- complete Google Cloud OAuth configuration
- creation of a `rclone` Google Drive remote
- `rclone` validation checks before DriveSync usage

## Current scope status

Available commands:

```bash
drivesync dir add <id> <directory>
drivesync dir add <id> <directory> --remote-dir archives/<id>
drivesync dir add <id> <directory> --create
drivesync dir remove <id>
drivesync dir list
drivesync dir list --json
drivesync dir show <id>
drivesync dir show <id> --json
drivesync sync check
drivesync sync check --json
drivesync sync run
drivesync sync run documents
drivesync sync run documents --resync
drivesync sync run documents --resync --force
drivesync sync run --json
drivesync sync status
drivesync sync status documents
drivesync sync status --json
drivesync status
drivesync status --json
drivesync status --executor
drivesync status documents --executor
drivesync sync logs
drivesync sync logs documents --path
drivesync sync logs documents --raw
drivesync sync logs documents --tail 20
drivesync sync logs documents --tail 20 --follow
drivesync sync logs --follow documents
drivesync sync logs documents --raw --tail 5
drivesync sync logs --json
drivesync schedule set documents --frequency hourly
drivesync schedule set documents --frequency daily --at 22:30
drivesync schedule set documents --frequency weekly --day sunday --at 03:00
drivesync schedule show documents
drivesync schedule list
drivesync schedule remove documents
drivesync schedule preview
drivesync schedule install
drivesync schedule uninstall
drivesync config logs precision show
drivesync config logs precision show --json
drivesync config logs precision set light
drivesync config logs precision set full
drivesync config logs max-size show
drivesync config logs max-size show --json
drivesync config logs max-size set 10
drivesync config logs max-size set 64
drivesync config root show
drivesync config root show --json
drivesync config root set Backups/DriveSync
drivesync config root reset
drivesync config path show
drivesync config path show --json
drivesync config path set ~/.drivesync
drivesync config path reset
drivesync auth setup
drivesync auth setup gdrive
drivesync auth setup --json
drivesync auth status
drivesync auth status --json
```

`sync status` displays the last known state by directory (or `never_run`).

In text output, `sync status` also displays the last known synchronization date.

`status` displays the health of every managed directory using its configured schedule
and the local synchronization history. It tolerates up to two schedule intervals to
avoid reporting a timer that is only slightly late as an error.

`status --json` exposes the global state and, for each directory, the schedule interval,
last attempt, last successful synchronization, result, and reason.

`status --executor` prints one compact indicator for the GNOME Executor extension:

- `☁️ 🟢` when everything is healthy;
- `☁️ 🟠` when a directory is late or its state is uncertain;
- `☁️ 🔴` after a real synchronization failure;
- `☁️ ⚪` when the configured remote is unavailable.

### Example with GNOME Executor

In Executor, add an active command to the status area and set its interval to
60 seconds:

```text
/home/olivier/scripts/drivesync/.venv/bin/drivesync status --executor
```

The result appears directly in the GNOME system bar:

```text
 ☁️ 🟢
```

Depending on the situation, the indicator changes to:

- `☁️ 🟠` for a late or uncertain state;
- `☁️ 🔴` after a real synchronization failure;
- `☁️ ⚪` when the remote is unavailable.

The path depends on your installation. Run `command -v drivesync` in a terminal
to find the path to use in Executor.

`sync logs` displays the DriveSync log of executions from the local `sync-history.jsonl` file.
`sync logs --raw` displays raw captured `rclone` output for debugging.
`sync logs --tail N` limits output to the last N events.
`sync logs --tail N --follow` keeps streaming new events until interrupted.
`sync logs --follow` starts with the last 10 events and keeps streaming new events; use `--tail N` to change the initial window.

Scheduling:

- `schedule` is the DriveSync business interface for scheduling
- the MVP backend relies on Linux `crontab`
- `schedule set/remove` modify the local DriveSync configuration
- `schedule install` applies the current local configuration to the user crontab
- `schedule uninstall` removes only the DriveSync-managed block from the user crontab, without erasing the local configuration
- after a `schedule set` or `schedule remove`, crontab does not change until `schedule install` or `schedule uninstall` is executed
- each scheduled execution launches `sync run` and is logged in the internal history

Recommended workflow:

- `schedule set ...` to record or modify the desired frequency
- `schedule preview` to verify the generated cron block
- `schedule install` to apply the current configuration to `crontab`
- `schedule remove ...` to remove a local entry that is no longer needed
- `schedule uninstall` to completely remove the DriveSync block from `crontab`

Supported frequencies in the MVP:

- `5minutes`
- `hourly`
- `daily --at HH:MM`
- `weekly --day monday..sunday --at HH:MM`

Log precision:

- `light`: light raw capture, sufficient for normal use
- `full`: more verbose `rclone` capture for in-depth diagnosis

Log history size and rotation:

- by default, `sync-history.jsonl` is rotated when its next write would exceed `10 KB`
- DriveSync archives the previous file to `sync-history-<timestamp>.jsonl`
- older archives are deleted automatically, only the latest archive is kept
- the threshold is configurable with `config logs max-size set <kb>`

Configuration:

```bash
drivesync config logs precision show
drivesync config logs precision set light
drivesync config logs precision set full
drivesync config logs max-size show
drivesync config logs max-size set 10
```

`--resync` security:

- this rule is independent of mapping collisions
- even with a single `dir` id and a unique `remote-dir`, if both local and remote are non-empty, DriveSync refuses `--resync` by default
- `--force` is only used to explicitly confirm this risky case

First synchronization of an id:

- DriveSync automatically attempts a `--resync` when bisync state is missing
- if local and remote are already non-empty, DriveSync does not auto-force and requires explicit confirmation
- in this case, run: `drivesync sync run <id> --resync --force`

By default, the remote root folder is `DriveSync/`.
`config root` configures the remote root directory used for all folders.
You can change this remote root folder with `config root set`.
With `--remote-dir`, you can bind a local folder to a specific remote subfolder.
A `remote-dir` can only be used once in the DriveSync configuration.

Example:

```bash
drivesync config root set Backups/DriveSync
drivesync config root show
```

If the local folder does not exist when running `dir add`, DriveSync prompts to create it interactively (`y/N`).
For scripts or non-interactive usage, use `--create`.

To set a custom config location via the tool:

```bash
drivesync config path set ~/.drivesync
drivesync config path show
```

To return to the default path:

```bash
drivesync config path reset
drivesync config path show
```