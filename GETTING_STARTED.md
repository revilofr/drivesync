# DriveSync - Lancement, tests et dependances

## Etat actuel du projet

Guide detaille OAuth Google Drive : [DRIVESYNC_GOOGLE_AUTH.md](DRIVESYNC_GOOGLE_AUTH.md)

Configurer le chemin de config via la CLI :

```bash
PYTHONPATH=. python3 -m drivesync config path set ~/.drivesync
PYTHONPATH=. python3 -m drivesync config path show
```

Le projet est en cours de construction.

Ce qui fonctionne actuellement :

- structure du package Python
- CLI `drivesync`
- commandes `dir add`, `dir remove`, `dir list` (avec mapping remote optionnel)
- creation interactive du dossier local manquant sur `dir add` (ou `--create`)
- commande `sync check` (preflight `rclone` + verification de version)
- commande `auth setup` (selection/validation d'un remote rclone et sauvegarde de la config)
- commande `auth status` (validation remote configure + accessibilite)
- commande `sync run` (lance `rclone bisync` sur un id ou sur tous les repertoires configures)
- configuration persistante de la precision des logs (`light` ou `full`)
- configuration persistante du dossier racine distant (`DriveSync` par defaut)
- planification MVP via `schedule` avec backend `crontab`
- tests unitaires sur cette premiere partie
- autocompletion Bash et Zsh

Ce qui n'est pas encore implemente :

- `auth reconnect`

Historique de sync :

- les executions `sync run` sont journalisees dans `sync-history.jsonl`
- `sync status` lit le dernier etat connu par id et affiche aussi la derniere date connue en sortie texte
- `sync logs` affiche le journal DriveSync
- `sync logs --raw` affiche la sortie brute capturee de `rclone`
- `config logs precision show|set` pilote le niveau de verbosite capture pour les prochains runs

Planification :

- `schedule` est la couche DriveSync pour planifier les synchronisations
- le backend MVP utilise la crontab utilisateur Linux
- `schedule set/remove` changent la configuration locale
- `schedule install/uninstall` appliquent ou retirent le bloc DriveSync dans la crontab
- apres un `schedule set` ou `schedule remove`, il faut executer `schedule install` ou `schedule uninstall` pour mettre a jour la crontab reelle
- une execution planifiee lance `sync run <id>` et est journalisee dans l'historique interne

Frequences supportees :

- `5minutes`
- `hourly`
- `daily --at HH:MM`
- `weekly --day monday..sunday --at HH:MM`

Racine distante :

- par defaut, DriveSync synchronise dans `DriveSync/<id>` sur le remote configure
- `config root` configure le remote root directory in cloud storage
- `config root set` permet de changer ce dossier racine distant, par exemple `Backups/DriveSync`
- `config root show|reset` permettent d'inspecter ou restaurer la valeur par defaut

## Python requis

Version minimale :

```text
Python 3.10
```

Cette contrainte est definie dans `pyproject.toml` :

```toml
requires-python = ">=3.10"
```

Verifier la version installee :

```bash
python3 --version
```

Exemple attendu :

```text
Python 3.10.x
```

ou plus recent.

## Installation de Python sur Ubuntu 24

Sur Ubuntu 24, la commande a utiliser est normalement `python3`, pas `python`.

Verifier d'abord si Python 3 est deja disponible :

```bash
python3 --version
```

Si la commande n'existe pas, installe les paquets de base :

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

Verifier ensuite :

```bash
python3 --version
python3 -m pip --version
```

Si tu tapes `python --version` et que la commande n'existe pas, ce n'est pas anormal sur Ubuntu 24.

Dans toute la documentation de ce projet, il faut utiliser :

```bash
python3
```

et non :

```bash
python
```

## Dependances du projet

### Dependances runtime (etat actuel)

- Linux
- Python `>= 3.10`
- bibliotheque standard Python uniquement
- aucune dependance Python tierce pour le MVP actuel

### Dependances outils (dev / install locale)

- `pip`
- `setuptools`

### Dependances systeme

- Linux
- `rclone` sera obligatoire pour les commandes `auth`, `sync check` et `sync run`
- `cron` est obligatoire pour `schedule install` et `schedule uninstall`
- `rsync` n'est pas une dependance de DriveSync

Note : pour les commandes `dir add/remove/list` de la V1 actuelle, `rclone` n'est pas necessaire.

## Faut-il installer rsync ?

Non.

DriveSync ne repose pas sur `rsync`.

L'outil cible pour la synchronisation est :

```text
rclone
```

Donc :

- pas besoin de `rsync`
- `rclone` sera necessaire plus tard pour les commandes de sync/auth/check
- pour le MVP actuel (`dir add/remove/list`), `rclone` n'est pas necessaire

## Faut-il installer rclone ?

Pas pour tester la partie actuellement implemente.

Oui pour la suite du projet, car DriveSync est pense comme une surcouche de `rclone`.

Quand `auth`, `sync check` et `sync run` sont utilises, `rclone` doit etre installe sur la machine cible.

### Comment verifier si `rclone` est installe

Commande minimale :

```bash
command -v rclone
```

Si `rclone` est installe, cette commande affiche un chemin, par exemple :

```text
/usr/bin/rclone
```

Si rien ne s'affiche, `rclone` n'est probablement pas installe.

Verifier si `rclone` est present :

```bash
command -v rclone
```

Pour confirmer proprement et voir la version :

```bash
rclone version
```

Si tu obtiens une erreur du type `command not found`, alors `rclone` n'est pas installe.

Dans l'environnement actuel, `rclone` n'est pas installe.

## Quelle version de rclone utiliser

Pour DriveSync, il ne faut pas viser une version ancienne de `rclone bisync`.

Recommandation pratique :

- minimum raisonnable : `rclone >= 1.66`
- version recommandee : `rclone >= 1.71`
- idealement : une version stable recente, par exemple `1.74.x` ou `1.75.x`

Pourquoi `1.66` comme minimum :

- `bisync` y devient nettement plus robuste
- `--recover` est disponible
- `--max-lock` est disponible
- la gestion moderne des comparaisons et de la recovery y est mieux posee
- le support de Google Docs dans `bisync` y est ameliore

Pourquoi `1.71` comme recommandation :

- `bisync` y est officiellement sorti de beta
- c'est un meilleur socle pour un outil qui privilegie la securite des donnees

Point important sur ta version actuelle :

```text
rclone v1.60.1-DEV
```

Cette version est trop ancienne pour servir de base confortable a la V1 de DriveSync si on veut s'appuyer sur les comportements modernes de `bisync`.

De plus, il vaut mieux eviter les versions `-DEV` pour un usage normal, sauf si tu sais exactement pourquoi tu utilises ce build.

## Installation de rclone sur Ubuntu

Pour les commandes futures de synchronisation, il faudra installer `rclone`.

Cette procedure n'inclut pas de desinstallation.

### Methode recommandee (script officiel)

```bash
sudo -v
curl https://rclone.org/install.sh | sudo bash
```

Verifier ensuite :

```bash
rclone version
```

La methode ci-dessus installe une version stable recente sans imposer de desinstallation prealable.

### Methode version precise (deb officiel)

Exemple avec `1.75.1` :

```bash
cd /tmp
curl -O https://downloads.rclone.org/v1.75.1/rclone-v1.75.1-linux-amd64.deb
sudo apt install ./rclone-v1.75.1-linux-amd64.deb
rclone version
```

Cette methode est utile si tu veux figer une version exacte.

### Option simple via apt

```bash
sudo apt update
sudo apt install rclone
```

Verifier ensuite :

```bash
rclone version
```

### Point important

La version disponible via `apt` depend de ta version d'Ubuntu et peut etre en retard par rapport aux versions stables recentes de `rclone`.

Comme DriveSync doit s'aligner sur le comportement reel de `rclone`, il faudra verifier les options disponibles sur ta machine avec :

```bash
rclone bisync --help
```

et au besoin :

```bash
rclone help flags
```

Dans cet environnement, je n'ai pas pu valider ces commandes car `rclone` n'y est pas installe.

## Arborescence utile

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

## Autocompletion shell

Activer Bash pour la session courante :

```bash
source /path/to/drivesync/completion.bash
```

Rendre persistant Bash :

```bash
echo "source /path/to/drivesync/completion.bash" >> ~/.bashrc
source ~/.bashrc
```

Activer Zsh pour la session courante :

```zsh
source /path/to/drivesync/completion.zsh
```

Rendre persistant Zsh :

```zsh
echo "source /path/to/drivesync/completion.zsh" >> ~/.zshrc
source ~/.zshrc
```

## Comment lancer le projet

Depuis la racine du repo :

```bash
cd /path/to/drivesync
```

### Methode 1 - execution directe en module Python

```bash
PYTHONPATH=. python3 -m drivesync dir list
```

Verifier aussi le preflight `rclone` :

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
PYTHONPATH=. python3 -m drivesync schedule set documents --frequency 5minutes
PYTHONPATH=. python3 -m drivesync schedule preview
PYTHONPATH=. python3 -m drivesync schedule install
PYTHONPATH=. python3 -m drivesync config path show
PYTHONPATH=. python3 -m drivesync config path show --json
```

Important pour la planification :

- `schedule set` et `schedule remove` modifient seulement la configuration DriveSync stockee localement
- `schedule install` ecrit cette configuration dans la crontab utilisateur
- `schedule uninstall` retire seulement le bloc DriveSync de la crontab et laisse la configuration locale intacte
- si la crontab contient encore une ancienne frequence, relancer `PYTHONPATH=. python3 -m drivesync schedule install`

Exemple de binding explicite local vers remote :

```bash
PYTHONPATH=. python3 -m drivesync dir add documents ~/Documents --remote-dir perso/documents
PYTHONPATH=. python3 -m drivesync sync run documents
```

Le remote effectif sera :

```text
<remote_configure>:<root>/perso/documents
```

Protection anti-ecrasement sur `--resync` :

- cette protection n'est pas liee au cas "deux ids vers le meme remote-dir"
- meme avec un mapping unique (1 id -> 1 remote-dir), si local et remote contiennent deja des fichiers, la commande est refusee
- pour confirmer explicitement ce cas, ajouter `--force`

Premier run d'un id :

- si l'etat bisync n'existe pas encore, DriveSync tente automatiquement un `--resync`
- exception de securite: si local et remote sont deja non vides, DriveSync demande une confirmation explicite
- dans ce cas, lancer `sync run <id> --resync --force`

Protection anti-collision de mapping :

- un sous-dossier remote (`--remote-dir`) ne peut pas etre partage entre deux ids `dir`
- cela evite que deux repertoires locaux distincts ecrivent sur la meme cible remote

Conflits de modification (meme fichier modifie des deux cotes) :

- la detection et la resolution de conflit sont gerees par `rclone bisync`
- les suffixes de conflits (ex: `.conflict1`, `.conflict2`) viennent de `rclone`, pas de DriveSync
- DriveSync orchestre uniquement l'execution et n'invente pas de schema de nommage de conflit

Exemples :

```bash
PYTHONPATH=. python3 -m drivesync dir add documents ~/Documents
PYTHONPATH=. python3 -m drivesync dir list
PYTHONPATH=. python3 -m drivesync dir list --json
PYTHONPATH=. python3 -m drivesync dir remove documents
```

### Methode 2 - installation locale du package

Si tu veux obtenir la commande `drivesync` directement dans ton environnement :

```bash
cd /path/to/drivesync
python3 -m venv .venv
. .venv/bin/activate
pip install .
```

Puis :

```bash
drivesync dir list
```

Remarque :

- `pip` et `setuptools` doivent etre disponibles pour cette methode
- si tu ne veux rien installer, la methode 1 suffit

Sur Ubuntu 24, installer avec `python3 -m pip install --user ...` peut etre bloque par PEP 668 (environnement Python externe gere par le systeme). La methode `venv` ci-dessus est la voie recommandee.

### Methode 3 - mode developpement (recommande)

Pour avoir la commande `drivesync` et refleter automatiquement les modifications du code sans reinstaller a chaque changement :

```bash
cd /path/to/drivesync
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Verifier ensuite :

```bash
drivesync --help
```

Activer l'autocompletion Bash :

```bash
source /path/to/drivesync/completion.bash
```

Si `drivesync` n'est pas trouve, ajoute `~/.local/bin` a ton `PATH` :

```bash
drivesync --help
```

Avec `venv`, la commande `drivesync` est disponible tant que l'environnement est active.

Pour l'avoir en permanence sans activer manuellement :

```bash
echo "alias drivesync='/path/to/drivesync/.venv/bin/drivesync'" >> ~/.bashrc
source ~/.bashrc
drivesync --help
```

### Methode 4 - alias shell (sans installation)

Si tu preferes ne pas installer le package, tu peux creer un alias :

```bash
echo "alias drivesync='PYTHONPATH=/path/to/drivesync python3 -m drivesync'" >> ~/.bashrc
source ~/.bashrc
drivesync --help
```

Avec cette methode, il suffit ensuite de taper `drivesync ...`.

### Option pipx (facultative)

Si tu preferes ne pas gerer de venv projet, tu peux utiliser `pipx` :

```bash
sudo apt update
sudo apt install pipx
pipx ensurepath
```

Puis, depuis le projet :

```bash
cd /path/to/drivesync
pipx install -e .
drivesync --help
```

## Comment tester

Lancer les tests unitaires :

```bash
cd /path/to/drivesync
python3 -m unittest discover -s tests
```

Resultat actuellement attendu :

```text
Ran 6 tests
OK
```

## Ou la configuration est stockee

Par defaut, DriveSync stocke sa configuration sous :

```text
~/.config/drivesync/
```

Les fichiers concernes a ce stade sont :

- `config.ini`
- `directories.conf`

## Variable utile pour les tests locaux

Pour eviter d'ecrire dans ta vraie configuration utilisateur pendant des essais manuels, tu peux rediriger le dossier de config :

```bash
export DRIVESYNC_CONFIG_HOME=/tmp/drivesync-dev-config
```

Puis lancer par exemple :

```bash
PYTHONPATH=. python3 -m drivesync dir add documents ~/Documents
PYTHONPATH=. python3 -m drivesync dir list
```

## Exemple de premier test manuel

```bash
cd /path/to/drivesync
export DRIVESYNC_CONFIG_HOME=/tmp/drivesync-dev-config
mkdir -p /tmp/drivesync-dev-config
PYTHONPATH=. python3 -m drivesync dir add documents ~/Documents
PYTHONPATH=. python3 -m drivesync dir list
PYTHONPATH=. python3 -m drivesync dir list --json
PYTHONPATH=. python3 -m drivesync dir remove documents
```

## Resume rapide

- Python requis : 3.10 ou plus recent
- Dependances Python applicatives : aucune
- `rsync` : inutile
- `rclone` : pas necessaire pour le MVP actuel, necessaire pour la suite
- Commande de lancement la plus simple : `PYTHONPATH=. python3 -m drivesync ...`
- Commande de test : `python3 -m unittest discover -s tests`