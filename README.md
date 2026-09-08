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
drivesync sync logs
drivesync sync logs documents --path
drivesync sync logs documents --raw
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
`sync logs` displays the DriveSync log of executions from the local `sync-history.jsonl` file.
`sync logs --raw` displays raw captured `rclone` output for debugging.

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

- DriveSync tente automatiquement un `--resync` si l'etat bisync est absent
- si local et remote sont deja non vides, DriveSync n'auto-force pas et demande une confirmation explicite
- dans ce cas, lancer : `drivesync sync run <id> --resync --force`

Par defaut, le dossier remote cible est DriveSync/<id>.
`config root` configure le remote root directory in cloud storage utilise pour tous les repertoires.
Vous pouvez donc changer ce dossier racine distant avec `config root set`.
Avec --remote-dir, vous pouvez binder un repertoire local vers un sous-dossier remote specifique.
Un `remote-dir` ne peut etre utilise qu'une seule fois dans la configuration DriveSync.

Exemple :

```bash
drivesync config root set Backups/DriveSync
drivesync config root show
```

Si le dossier local n'existe pas lors d'un `dir add`, DriveSync propose sa creation en interactif (`y/N`).
Pour les scripts ou un usage non-interactif, utilisez `--create`.

Pour definir un emplacement de config personnalise via l'outil :

```bash
drivesync config path set ~/.drivesync
drivesync config path show
```

Pour revenir au chemin standard :

```bash
drivesync config path reset
drivesync config path show
```