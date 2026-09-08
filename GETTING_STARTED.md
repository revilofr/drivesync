# DriveSync - Getting started, tests, and dependencies

## Current project state

Detailed Google Drive OAuth guide: [DRIVESYNC_GOOGLE_AUTH.md](DRIVESYNC_GOOGLE_AUTH.md)

Set the config path via the CLI:

```bash
PYTHONPATH=. python3 -m drivesync config path set ~/.drivesync
PYTHONPATH=. python3 -m drivesync config path show
```

The project is under construction.

## What works currently:

- Python package structure
- CLI `drivesync`
- commands `dir add`, `dir remove`, `dir list` (with optional remote mapping)
- interactive creation of missing local folder on `dir add` (or `--create`)
- command `sync check` (rclone preflight + version check)
- command `auth setup` (select/validate an rclone remote and save config)
- command `auth status` (validate configured remote + accessibility)
- command `sync run` (launches `rclone bisync` on an id or on all configured directories)
- persistent configuration of log precision (`light` or `full`)
- persistent configuration of remote root folder (`DriveSync` by default)
- MVP scheduling via `schedule` with `crontab` backend
- unit tests on this first part
- Bash and Zsh autocompletion

## What is not yet implemented:

- `auth reconnect`

## Sync history:

- `sync run` executions are logged in `sync-history.jsonl`
- `sync status` reads the last known state by id and also displays the last known date in text output
- `sync logs` displays the DriveSync journal
- `sync logs --raw` displays the raw captured output of `rclone`
- `config logs precision show|set` controls the verbosity level captured for next runs
- `config logs max-size show|set` controls max size of `sync-history.jsonl` in KB (default: 10)
- when max size is exceeded, DriveSync archives current history to `sync-history-<timestamp>.jsonl`, starts a new `sync-history.jsonl`, and keeps only the latest archive

## Scheduling:

- `schedule` is the DriveSync layer for scheduling synchronizations
- the MVP backend uses the Linux user crontab
- `schedule set/remove` change the local configuration
- `schedule install/uninstall` apply or remove the DriveSync block in crontab
- after a `schedule set` or `schedule remove`, you must run `schedule install` or `schedule uninstall` to update the actual crontab
- a scheduled execution launches `sync run <id>` and is logged in the internal history

## Supported frequencies:

- `5minutes`
- `hourly`
- `daily --at HH:MM`
- `weekly --day monday..sunday --at HH:MM`

## Remote root:

- by default, DriveSync synchronizes in `DriveSync/<id>` on the configured remote
- `config root` configures the remote root directory in cloud storage
- `config root set` allows you to change this remote root folder, for example `Backups/DriveSync`
- `config root show|reset` allow you to inspect or restore the default value

## Required Python

Minimum version:

```text
Python 3.10
```

This constraint is defined in `pyproject.toml`:

```toml
requires-python = ">=3.10"
```

Check the installed version:

```bash
python3 --version
```

Expected example:

```text
Python 3.10.x
```

or later.

## Python installation on Ubuntu 24

On Ubuntu 24, the command to use is normally `python3`, not `python`.

First check if Python 3 is already available:

```bash
python3 --version
```

If the command does not exist, install the basic packages:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

Then verify:

```bash
python3 --version
python3 -m pip --version
```

If you type `python --version` and the command does not exist, this is normal on Ubuntu 24.

Throughout this project documentation, you must use:

```bash
python3
```

and not:

```bash
python
```

## Project dependencies

### Runtime dependencies (current state)

- Linux
- Python `>= 3.10`
- Python standard library only
- no third-party Python dependency for the current MVP

### Tool dependencies (dev / local install)

- `pip`
- `setuptools`

### System dependencies

- Linux
- `rclone` will be required for `auth`, `sync check`, and `sync run` commands
- `cron` is required for `schedule install` and `schedule uninstall`
- `rsync` is not a dependency of DriveSync

Note: for V1 current commands `dir add/remove/list`, `rclone` is not required.

## Do I need to install rsync?

No.

DriveSync does not rely on `rsync`.

The target tool for synchronization is:

```text
rclone
```

So:

- no need for `rsync`
- `rclone` will be required later for sync/auth/check commands
- for the current MVP (`dir add/remove/list`), `rclone` is not required

## Do I need to install rclone?

Not to test the currently implemented part.

Yes for the continuation of the project, because DriveSync is designed as a layer above `rclone`.

When `auth`, `sync check`, and `sync run` are used, `rclone` must be installed on the target machine.

### How to check if `rclone` is installed

Minimal command:

```bash
command -v rclone
```

If `rclone` is installed, this command displays a path, for example:

```text
/usr/bin/rclone
```

If nothing is displayed, `rclone` is probably not installed.

Check if `rclone` is present:

```bash
command -v rclone
```

To confirm properly and see the version:

```bash
rclone version
```

If you get an error like `command not found`, then `rclone` is not installed.

In the current environment, `rclone` is not installed.

## Which version of rclone to use

For DriveSync, you should not target an old version of `rclone bisync`.

Practical recommendation:

- reasonable minimum: `rclone >= 1.66`
- recommended version: `rclone >= 1.71`
- ideally: a recent stable version, for example `1.74.x` or `1.75.x`

Why `1.66` as minimum:

- `bisync` becomes significantly more robust there
- `--recover` is available
- `--max-lock` is available
- modern comparison and recovery management is better established there
- Google Docs support in `bisync` is improved there

Why `1.71` as recommendation:

- `bisync` officially exited beta there
- it is a better foundation for a tool that prioritizes data security

Important point about your current version:

```text
rclone v1.60.1-DEV
```

This version is too old to comfortably serve as a base for DriveSync V1 if you want to rely on modern `bisync` behaviors.

Also, it is better to avoid `-DEV` versions for normal use, unless you know exactly why you are using this build.

## Installing rclone on Ubuntu

For future synchronization commands, you will need to install `rclone`.

This procedure does not include uninstallation.

### Recommended method (official script)

```bash
sudo -v
curl https://rclone.org/install.sh | sudo bash
```

Then verify:

```bash
rclone version
```

The above method installs a recent stable version without requiring prior uninstallation.

### Specific version method (official deb)

Example with `1.75.1`:

```bash
cd /tmp
curl -O https://downloads.rclone.org/v1.75.1/rclone-v1.75.1-linux-amd64.deb
sudo apt install ./rclone-v1.75.1-linux-amd64.deb
rclone version
```

This method is useful if you want to pin an exact version.

### Simple option via apt

```bash
sudo apt update
sudo apt install rclone
```

Then verify:

```bash
rclone version
```

### Important point

The version available via `apt` depends on your Ubuntu version and may lag behind recent stable `rclone` versions.

As DriveSync must align with actual `rclone` behavior, you will need to check available options on your machine with:

```bash
rclone bisync --help
```

and if needed:

```bash
rclone help flags
```

In this environment, I was unable to validate these commands because `rclone` is not installed there.

## Useful directory structure

```text
drivesync/
├── drivesync/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   └── directories.py
├── tests/
│   └── test_directories.py
├── GETTING_STARTED.md
├── pyproject.toml
└── README.md
```

## Shell autocompletion

Enable Bash for the current session:

```bash
source /path/to/drivesync/completion.bash
```

Make Bash persistent:

```bash
echo "source /path/to/drivesync/completion.bash" >> ~/.bashrc
source ~/.bashrc
```

Enable Zsh for the current session:

```zsh
source /path/to/drivesync/completion.zsh
```

Make Zsh persistent:

```zsh
echo "source /path/to/drivesync/completion.zsh" >> ~/.zshrc
source ~/.zshrc
```

## How to run the project

From the repo root:

```bash
cd /path/to/drivesync
```

### Method 1 - direct execution as a Python module

```bash
PYTHONPATH=. python3 -m drivesync dir list
```

Also verify the `rclone` preflight:

```bash
PYTHONPATH=. python3 -m drivesync sync check
PYTHONPATH=. python3 -m drivesync sync check --json
PYTHONPATH=. python3 -m drivesync auth setup
PYTHONPATH=. python3 -m drivesync auth setup gdrive
PYTHONPATH=. python3 -m drivesync auth setup --json
PYTHONPATH=. python3 -m drivesync auth status
PYTHONPATH=. python3 -m drivesync auth status --json
PYTHONPATH=. python3 -m drivesync sync run
PYTHONPATH=. python3 -m drivesync sync run documents
PYTHONPATH=. python3 -m drivesync sync run documents --resync
PYTHONPATH=. python3 -m drivesync sync run documents --resync --force
PYTHONPATH=. python3 -m drivesync sync run --json
PYTHONPATH=. python3 -m drivesync sync status
PYTHONPATH=. python3 -m drivesync sync status --json
PYTHONPATH=. python3 -m drivesync sync logs
PYTHONPATH=. python3 -m drivesync sync logs --json
PYTHONPATH=. python3 -m drivesync sync logs documents --path
PYTHONPATH=. python3 -m drivesync sync logs documents --tail 20
PYTHONPATH=. python3 -m drivesync sync logs documents --tail 20 --follow
PYTHONPATH=. python3 -m drivesync sync logs documents --raw --tail 5
PYTHONPATH=. python3 -m drivesync schedule set documents --frequency 5minutes
PYTHONPATH=. python3 -m drivesync schedule preview
PYTHONPATH=. python3 -m drivesync schedule install
PYTHONPATH=. python3 -m drivesync config path show
PYTHONPATH=. python3 -m drivesync config path show --json
PYTHONPATH=. python3 -m drivesync config logs max-size show
PYTHONPATH=. python3 -m drivesync config logs max-size show --json
PYTHONPATH=. python3 -m drivesync config logs max-size set 10
```

Important for scheduling:

- `schedule set` and `schedule remove` only modify the locally stored DriveSync configuration
- `schedule install` writes this configuration to the user crontab
- `schedule uninstall` removes only the DriveSync block from crontab and leaves the local configuration intact
- if crontab still contains an old frequency, rerun `PYTHONPATH=. python3 -m drivesync schedule install`

Example of explicit local to remote binding:

```bash
PYTHONPATH=. python3 -m drivesync dir add documents ~/Documents --remote-dir perso/documents
PYTHONPATH=. python3 -m drivesync sync run documents
```

The effective remote will be:

```text
<remote_configure>:<root>/perso/documents
```

Anti-overwrite protection on `--resync`:

- this protection is not related to the "two ids to the same remote-dir" case
- even with a unique mapping (1 id -> 1 remote-dir), if local and remote already contain files, the command is refused
- to explicitly confirm this case, add `--force`

First run of an id:

- if bisync state does not exist yet, DriveSync automatically attempts a `--resync`
- security exception: if local and remote are already non-empty, DriveSync requests explicit confirmation
- in this case, run `sync run <id> --resync --force`

Anti-collision mapping protection:

- a remote subfolder (`--remote-dir`) cannot be shared between two `dir` ids
- this prevents two separate local directories from writing to the same remote target

Conflict modifications (same file modified on both sides):

- conflict detection and resolution are managed by `rclone bisync`
- conflict suffixes (eg `.conflict1`, `.conflict2`) come from `rclone`, not DriveSync
- DriveSync only orchestrates execution and does not invent a conflict naming scheme

Examples:

```bash
PYTHONPATH=. python3 -m drivesync dir add documents ~/Documents
PYTHONPATH=. python3 -m drivesync dir list
PYTHONPATH=. python3 -m drivesync dir list --json
PYTHONPATH=. python3 -m drivesync dir remove documents
```

### Method 2 - local package installation

If you want to get the `drivesync` command directly in your environment:

```bash
cd /path/to/drivesync
python3 -m venv .venv
. .venv/bin/activate
pip install .
```

Then:

```bash
drivesync dir list
```

Note:

- `pip` and `setuptools` must be available for this method
- if you don't want to install anything, method 1 is sufficient

On Ubuntu 24, installing with `python3 -m pip install --user ...` may be blocked by PEP 668 (Python environment managed by the system). The `venv` method above is the recommended approach.

### Method 3 - development mode (recommended)

To get the `drivesync` command and automatically reflect code changes without reinstalling each time:

```bash
cd /path/to/drivesync
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Then verify:

```bash
drivesync --help
```

Enable Bash autocompletion:

```bash
source /path/to/drivesync/completion.bash
```

If `drivesync` is not found, add `~/.local/bin` to your `PATH`:

```bash
drivesync --help
```

With `venv`, the `drivesync` command is available as long as the environment is active.

To have it permanently without manually activating:

```bash
echo "alias drivesync='/path/to/drivesync/.venv/bin/drivesync'" >> ~/.bashrc
source ~/.bashrc
drivesync --help
```

### Method 4 - shell alias (without installation)

If you prefer not to install the package, you can create an alias:

```bash
echo "alias drivesync='PYTHONPATH=/path/to/drivesync python3 -m drivesync'" >> ~/.bashrc
source ~/.bashrc
drivesync --help
```

With this method, you then just need to type `drivesync ...`.

### Optional pipx option

If you prefer not to manage project venv, you can use `pipx`:

```bash
sudo apt update
sudo apt install pipx
pipx ensurepath
```

Then, from the project:

```bash
cd /path/to/drivesync
pipx install -e .
drivesync --help
```

## How to test

Run the unit tests:

```bash
cd /path/to/drivesync
python3 -m unittest discover -s tests
```

Currently expected result:

```text
Ran 6 tests
OK
```

## Where configuration is stored

By default, DriveSync stores its configuration under:

```text
~/.config/drivesync/
```

The files involved at this stage are:

- `config.ini`
- `directories.conf`

## Useful variable for local tests

To avoid writing to your real user configuration during manual tests, you can redirect the config folder:

```bash
export DRIVESYNC_CONFIG_HOME=/tmp/drivesync-dev-config
```

Then run for example:

```bash
PYTHONPATH=. python3 -m drivesync dir add documents ~/Documents
PYTHONPATH=. python3 -m drivesync dir list
```

## Example of first manual test

```bash
cd /path/to/drivesync
export DRIVESYNC_CONFIG_HOME=/tmp/drivesync-dev-config
mkdir -p /tmp/drivesync-dev-config
PYTHONPATH=. python3 -m drivesync dir add documents ~/Documents
PYTHONPATH=. python3 -m drivesync dir list
PYTHONPATH=. python3 -m drivesync dir list --json
PYTHONPATH=. python3 -m drivesync dir remove documents
```

## Quick summary

- Python requis : 3.10 ou plus recent
- Dependances Python applicatives : aucune
- `rsync` : inutile
- `rclone` : pas necessaire pour le MVP actuel, necessaire pour la suite
- Commande de lancement la plus simple : `PYTHONPATH=. python3 -m drivesync ...`
- Commande de test : `python3 -m unittest discover -s tests`