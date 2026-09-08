# DriveSync

DriveSync est une petite CLI Linux qui orchestre `rclone` pour des synchronisations simples de repertoires locaux.

Etat actuel du projet :

- stockage de configuration
- enregistrement des repertoires geres
- listing et suppression des repertoires enregistres

Le moteur de synchronisation est volontairement delegue a `rclone`.

La documentation de prise en main est dans [GETTING_STARTED.md](GETTING_STARTED.md).
La documentation detaillee OAuth Google Drive est dans [DRIVESYNC_GOOGLE_AUTH.md](DRIVESYNC_GOOGLE_AUTH.md).

## Projet

DriveSync a ete cree par `revilofr`, avec l'aide de Claude.

Le projet est open source et tout le monde est le bienvenu pour l'utiliser, le cloner, l'ameliorer et l'adapter a ses besoins.

## Lancement rapide

Depuis la racine du projet :

```bash
PYTHONPATH=. python3 -m drivesync dir list
```

Commande courte `drivesync` (sans `python3 -m`) sur Ubuntu 24 :

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Puis verifier :

```bash
drivesync --help
```

Option sans activer l'environnement a chaque session :

```bash
echo "alias drivesync='/path/to/drivesync/.venv/bin/drivesync'" >> ~/.bashrc
source ~/.bashrc
drivesync --help
```

Activer l'autocompletion Bash :

```bash
source /path/to/drivesync/completion.bash
```

Activer l'autocompletion Zsh :

```zsh
source /path/to/drivesync/completion.zsh
```

Activation persistante :

```bash
echo "source /path/to/drivesync/completion.bash" >> ~/.bashrc
source ~/.bashrc
```

Activation persistante Zsh :

```zsh
echo "source /path/to/drivesync/completion.zsh" >> ~/.zshrc
source ~/.zshrc
```

## Tests

Lancer la suite de tests :

```bash
python3 -m unittest discover -s tests
```

## Prerequis

- Linux
- Python 3.10 ou plus recent
- aucune dependance Python applicative externe pour le MVP actuel
- `rclone` est necessaire pour `auth`, `sync check` et `sync run`, mais pas pour `dir add/remove/list/show`
- `cron` est necessaire pour `schedule install` et `schedule uninstall`

## Dependances

Dependances runtime (etat actuel) :

- Python 3.10+
- bibliotheque standard Python uniquement

Dependances outils (developpement / installation locale) :

- `pip`
- `setuptools`

Dependances systeme :

- Linux
- `rclone` (obligatoire pour `auth`, `sync check` et `sync run`)
- `cron` (obligatoire pour `schedule install` et `schedule uninstall`)
- `rsync` n'est pas une dependance

Version `rclone` recommandee pour DriveSync :

- minimum raisonnable : `>= 1.66`
- recommande : `>= 1.71`
- idealement : une version stable recente

Verifier si `rclone` est installe :

```bash
command -v rclone
```

Verifier aussi sa version :

```bash
rclone version
```

## Documentation

Voir [GETTING_STARTED.md](GETTING_STARTED.md) pour :

- l'installation locale
- la procedure d'installation de `rclone` (sans desinstallation)
- les commandes de lancement
- les tests
- le stockage de configuration
- l'installation de `rclone` sur Ubuntu

Voir [DRIVESYNC_GOOGLE_AUTH.md](DRIVESYNC_GOOGLE_AUTH.md) pour :

- la configuration complete Google Cloud OAuth
- la creation d'un remote `rclone` Google Drive
- les checks de validation `rclone` avant usage DriveSync

## Etat du scope actuel

Commandes disponibles :

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

`sync status` affiche le dernier etat connu par repertoire (ou `never_run`).
En sortie texte, `sync status` affiche aussi la date de derniere synchronisation connue.
`sync logs` affiche le journal DriveSync des executions depuis le fichier local `sync-history.jsonl`.
`sync logs --raw` affiche la sortie brute capturee de `rclone` pour debug.

Planification :

- `schedule` est l'interface metier DriveSync pour la planification
- le backend MVP s'appuie sur `crontab` sous Linux
- `schedule set/remove` modifient la configuration locale DriveSync
- `schedule install` applique la configuration locale courante dans la crontab utilisateur
- `schedule uninstall` retire uniquement le bloc gere par DriveSync dans la crontab utilisateur, sans effacer la configuration locale
- apres un `schedule set` ou `schedule remove`, la crontab ne change pas tant que `schedule install` ou `schedule uninstall` n'a pas ete execute
- chaque execution planifiee lance `sync run` et est journalisee dans l'historique interne

Workflow recommande :

- `schedule set ...` pour enregistrer ou modifier la frequence voulue
- `schedule preview` pour verifier le bloc cron genere
- `schedule install` pour appliquer la configuration courante dans `crontab`
- `schedule remove ...` pour retirer une entree locale devenue inutile
- `schedule uninstall` si tu veux retirer completement le bloc DriveSync de `crontab`

Frequences supportees dans le MVP :

- `5minutes`
- `hourly`
- `daily --at HH:MM`
- `weekly --day monday..sunday --at HH:MM`

Precision de logs :

- `light` : capture brute legere, suffisante pour l'usage courant
- `full` : capture plus verbeuse de `rclone` pour diagnostic approfondi

Configuration :

```bash
drivesync config logs precision show
drivesync config logs precision set light
drivesync config logs precision set full
```

Securite `--resync`:

- cette regle est independante des collisions de mapping
- meme avec un seul id `dir` et un `remote-dir` unique, si local et remote sont tous les deux non vides, DriveSync refuse `--resync` par defaut
- `--force` sert uniquement a confirmer explicitement ce cas risque

Premiere synchronisation d'un id :

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