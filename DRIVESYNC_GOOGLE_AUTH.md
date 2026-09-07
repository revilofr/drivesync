# DriveSync — Configuration Google Drive avec rclone

Ce document décrit la procédure pas à pas utilisée pour configurer un accès Google Drive personnel avec `rclone`, afin de l'utiliser ensuite avec DriveSync.

> Objectif : permettre à `rclone` d'accéder à un compte Google Drive personnel via OAuth 2.0, avec un Client ID Google dédié.

---

## 1. Prérequis

- Un compte Google personnel
- Un projet Google Cloud
- `rclone` installé sur la machine Linux
- Un navigateur web disponible sur la machine

Vérifier que `rclone` est installé :

```bash
rclone version
```

---

## 2. Créer un projet Google Cloud

Se connecter à Google Cloud Console avec le compte Google qui sera utilisé pour DriveSync.

Créer un nouveau projet, par exemple :

```text
DriveSync
```

Conserver ce projet pour toute la configuration OAuth et Google Drive API.

---

## 3. Configurer Google Auth Platform

Dans le projet Google Cloud :

```text
Google Auth Platform
```

Configurer l'application OAuth.

### Type d'audience

Choisir :

```text
Externe
```

`Interne` est réservé aux organisations Google Workspace / Cloud Identity.

Le mode `Externe` ne signifie pas que tout le monde peut accéder au Drive.  
Chaque utilisateur doit explicitement autoriser l'application.

En mode test, seuls les comptes ajoutés dans la liste des utilisateurs test peuvent utiliser l'application.

---

## 4. Ajouter l'utilisateur test

Dans :

```text
Google Auth Platform
→ Audience
→ Utilisateurs test
```

Ajouter le compte Google personnel qui sera utilisé avec rclone.

Exemple :

```text
mon.compte@gmail.com
```

Pendant la phase de test, seuls les utilisateurs présents dans cette liste peuvent autoriser l'application.

---

## 5. Créer un OAuth Client ID

Dans :

```text
Google Auth Platform
→ Clients
→ Create client
```

Créer un client OAuth avec le type :

```text
Desktop app
```

Nom conseillé :

```text
DriveSync
```

Google fournit ensuite :

- `Client ID`
- `Client Secret`

Le Client ID ressemble généralement à :

```text
123456789-xxxxxxxxxxxxxxxx.apps.googleusercontent.com
```

Le Client Secret ressemble généralement à :

```text
GOCSPX-xxxxxxxxxxxxxxxx
```

### Important

Toujours utiliser le `Client ID` et le `Client Secret` provenant du **même client OAuth**.

Si nécessaire, télécharger le fichier JSON du client OAuth et récupérer directement :

```json
{
  "installed": {
    "client_id": "...apps.googleusercontent.com",
    "client_secret": "GOCSPX-..."
  }
}
```

---

## 6. Activer Google Drive API

Dans le projet Google Cloud, ouvrir :

```text
APIs & Services
→ Library
```

Chercher :

```text
Google Drive API
```

Puis cliquer sur :

```text
Enable
```

L'API correspond au service :

```text
drive.googleapis.com
```

Après activation, attendre éventuellement quelques minutes avant de retester.

### Erreur typique si l'API n'est pas activée

```text
Google Drive API has not been used in project ... before or it is disabled
```

ou :

```text
accessNotConfigured
```

Dans ce cas, activer simplement Google Drive API dans le projet concerné.

---

## 7. Lancer la configuration rclone

Lancer :

```bash
rclone config
```

Créer un nouveau remote.

Donner un nom explicite, par exemple :

```text
gdrive-personal
```

Choisir Google Drive comme backend.

---

## 8. Renseigner le Client ID et le Client Secret

Lorsque rclone demande :

```text
client_id>
```

coller le Client ID OAuth créé précédemment.

Puis lorsque rclone demande :

```text
client_secret>
```

coller le Client Secret correspondant.

### Erreur typique

```text
oauth2: "invalid_client" "The provided client secret is invalid."
```

Cela signifie généralement :

- mauvais Client Secret ;
- Client Secret provenant d'un autre client OAuth ;
- erreur de copier-coller.

Dans ce cas, revenir dans Google Cloud et recopier les deux valeurs depuis le même client OAuth.

---

## 9. Choisir le scope Google Drive

rclone propose plusieurs scopes :

```text
1 / Full access all files, excluding Application Data Folder.
    (drive)

2 / Read-only access.
    (drive.readonly)

3 / Access to files created by rclone only.
    (drive.file)

4 / Application Data folder.
    (drive.appfolder)

5 / Metadata read-only.
    (drive.metadata.readonly)
```

Pour DriveSync et `rclone bisync`, choisir :

```text
1
```

soit :

```text
drive
```

Pourquoi :

`bisync` doit pouvoir :

- lire ;
- créer ;
- modifier ;
- renommer ;
- supprimer ;

les fichiers présents des deux côtés.

Le scope `drive.file` est trop restrictif pour ce cas, car il limite l'accès aux fichiers créés ou explicitement autorisés via l'application.

---

## 10. Service Account

Lorsque rclone demande :

```text
service_account_file>
```

laisser vide :

```text
[Entrée]
```

Un Service Account n'est pas nécessaire pour un compte Google personnel avec authentification interactive OAuth.

---

## 11. Configuration avancée

Lorsque rclone demande :

```text
Edit advanced config?
```

répondre :

```text
n
```

Pour un usage standard DriveSync, les options avancées ne sont pas nécessaires.

---

## 12. Authentification via navigateur

Lorsque rclone demande :

```text
Use web browser to automatically authenticate rclone with remote?
```

répondre :

```text
y
```

rclone démarre alors un serveur HTTP local et ouvre le navigateur.

Exemple :

```text
http://127.0.0.1:53682/
```

Le flux est alors :

```text
rclone
  ↓
navigateur
  ↓
connexion Google
  ↓
autorisation OAuth
  ↓
retour vers http://127.0.0.1:53682/
  ↓
rclone récupère le code OAuth
```

Messages normaux :

```text
NOTICE: Waiting for code...
NOTICE: Got code
```

---

## 13. Redirect URL

Avec un client OAuth personnalisé, rclone peut afficher :

```text
Make sure your Redirect URL is set to "http://127.0.0.1:53682/" in your custom config.
```

Pour un client de type `Desktop app`, cette URL locale est utilisée par rclone pour récupérer le résultat de l'authentification.

---

## 14. Erreur 403 — utilisateur non autorisé

Erreur possible :

```text
Accès bloqué : rclone n'a pas terminé la procédure de validation de Google
Erreur 403 : access_denied
```

Si l'application est en mode test, vérifier :

```text
Google Auth Platform
→ Audience
→ Utilisateurs test
```

et ajouter le compte Google utilisé pour l'authentification.

Exemple :

```text
mon.compte@gmail.com
```

Puis recommencer l'authentification rclone.

---

## 15. Shared Drive

rclone demande ensuite :

```text
Configure this as a Shared Drive (Team Drive)?
```

Pour un Google Drive personnel, répondre :

```text
n
```

Les Shared Drives concernent principalement Google Workspace.

---

## 16. Valider le remote

rclone affiche ensuite quelque chose comme :

```text
Keep this "gdrive-personal" remote?

y) Yes this is OK
e) Edit this remote
d) Delete this remote
```

Répondre :

```text
y
```

Le remote est alors enregistré dans la configuration rclone.

---

## 17. Vérifier que l'accès fonctionne

Tester le remote avec :

```bash
rclone lsd "gdrive-personal:"
```

Si la configuration est correcte, rclone doit afficher les dossiers présents à la racine du Google Drive.

Exemple :

```text
          -1 2026-09-07 15:00:00        -1 Documents
          -1 2026-09-07 15:00:00        -1 Photos
          -1 2026-09-07 15:00:00        -1 DriveSync
```

À ce stade :

```text
OAuth                ✅
Client ID            ✅
Client Secret        ✅
Utilisateur test     ✅
Google Drive API     ✅
Remote rclone        ✅
Accès Google Drive   ✅
```

---

# Vérifications utiles

## Afficher les remotes configurés

```bash
rclone listremotes
```

---

## Afficher la configuration en masquant les secrets

```bash
rclone config redacted "gdrive-personal"
```

---

## Afficher le chemin du fichier de configuration rclone

```bash
rclone config file
```

---

# Sécurité

DriveSync ne doit jamais gérer directement :

- le mot de passe Google ;
- l'Access Token OAuth ;
- le Refresh Token OAuth ;
- le Client Secret dans sa propre configuration.

Ces informations restent sous la responsabilité de `rclone`.

DriveSync doit uniquement connaître le nom du remote utilisé.

Exemple :

```ini
[drive]
remote = gdrive-personal
root = DriveSync
```

---

# Architecture retenue

```text
DriveSync
    │
    ├── configuration des dossiers
    ├── status
    ├── check
    ├── orchestration
    │
    ▼
rclone
    │
    ├── OAuth Google
    ├── tokens
    ├── Google Drive API
    ├── bisync
    ├── conflits
    ├── recovery
    └── logs
```

Principe :

> DriveSync ne réimplémente jamais une fonctionnalité déjà correctement fournie par rclone.

---

# Prochaine étape

Une fois l'authentification validée, ne pas commencer directement avec `~/Documents`.

Créer d'abord un petit répertoire de test, par exemple :

```bash
mkdir -p ~/DriveSync-Test
```

Puis utiliser ce dossier pour valider :

- création locale → Google Drive ;
- création Google Drive → local ;
- modification locale ;
- modification distante ;
- suppression ;
- conflit ;
- fonctionnement offline ;
- reprise après reconnexion.

Une fois ces tests validés, la synchronisation de `~/Documents` pourra être configurée.
