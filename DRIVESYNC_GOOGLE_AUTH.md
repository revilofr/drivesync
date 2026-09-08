# DriveSync — Configuring Google Drive with rclone

This document describes the step-by-step procedure to configure personal Google Drive access with `rclone`, for use with DriveSync.

> Goal: allow `rclone` to access a personal Google Drive account via OAuth 2.0, with a dedicated Google Client ID.

---

## 1. Prerequisites

- A personal Google account
- A Google Cloud project
- `rclone` installed on the Linux machine
- A web browser available on the machine

Verify that `rclone` is installed:

```bash
rclone version
```

---

## 2. Create a Google Cloud project

Log in to Google Cloud Console with the Google account that will be used for DriveSync.

Create a new project, for example:

```text
DriveSync
```

Keep this project for all OAuth configuration and Google Drive API setup.

---

## 3. Configure Google Auth Platform

In the Google Cloud project:

```text
Google Auth Platform
```

Configure the OAuth application.

### Audience type

Choose:

```text
External
```

`Internal` is reserved for Google Workspace / Cloud Identity organizations.

External mode does not mean everyone can access the Drive.  
Each user must explicitly authorize the application.

In test mode, only accounts added to the test user list can use the application.

---

## 4. Add the test user

In:

```text
Google Auth Platform
→ Audience
→ Test users
```

Add the personal Google account that will be used with rclone.

Example:

```text
my.account@gmail.com
```

During the test phase, only users in this list can authorize the application.

---

## 5. Create an OAuth Client ID

In:

```text
Google Auth Platform
→ Clients
→ Create client
```

Create an OAuth client with type:

```text
Desktop app
```

Suggested name:

```text
DriveSync
```

Google then provides:

- `Client ID`
- `Client Secret`

The Client ID typically looks like:

```text
123456789-xxxxxxxxxxxxxxxx.apps.googleusercontent.com
```

The Client Secret typically looks like:

```text
GOCSPX-xxxxxxxxxxxxxxxx
```

### Important

Always use the `Client ID` and `Client Secret` from the **same OAuth client**.

If needed, download the JSON file of the OAuth client and retrieve directly:

```json
{
  "installed": {
    "client_id": "...apps.googleusercontent.com",
    "client_secret": "GOCSPX-..."
  }
}
```

---

## 6. Enable Google Drive API

In the Google Cloud project, open:

```text
APIs & Services
→ Library
```

Search for:

```text
Google Drive API
```

Then click:

```text
Enable
```

The API corresponds to the service:

```text
drive.googleapis.com
```

After enabling, wait a few minutes before retesting.

### Typical error if the API is not enabled

```text
Google Drive API has not been used in project ... before or it is disabled
```

or:

```text
accessNotConfigured
```

In this case, simply enable Google Drive API in the relevant project.

---

## 7. Start rclone configuration

Run:

```bash
rclone config
```

Create a new remote.

Give it an explicit name, for example:

```text
gdrive-personal
```

Choose Google Drive as the backend.

---

## 8. Enter the Client ID and Client Secret

When rclone asks:

```text
client_id>
```

paste the OAuth Client ID created earlier.

Then when rclone asks:

```text
client_secret>
```

paste the corresponding Client Secret.

### Typical error

```text
oauth2: "invalid_client" "The provided client secret is invalid."
```

This usually means:

- wrong Client Secret;
- Client Secret from a different OAuth client;
- copy-paste error.

In this case, go back to Google Cloud and recopy both values from the same OAuth client.

---

## 9. Choose the Google Drive scope

rclone offers several scopes:

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

For DriveSync and `rclone bisync`, choose:

```text
1
```

or:

```text
drive
```

Why:

`bisync` must be able to:

- read;
- create;
- modify;
- rename;
- delete;

files present on both sides.

The `drive.file` scope is too restrictive for this use case, as it limits access to files created or explicitly authorized by the application.

---

## 10. Service Account

When rclone asks:

```text
service_account_file>
```

leave it empty:

```text
[Enter]
```

A Service Account is not necessary for a personal Google account with interactive OAuth authentication.

---

## 11. Advanced configuration

When rclone asks:

```text
Edit advanced config?
```

answer:

```text
n
```

For standard DriveSync usage, advanced options are not necessary.

---

## 12. Browser authentication

When rclone asks:

```text
Use web browser to automatically authenticate rclone with remote?
```

answer:

```text
y
```

rclone then starts a local HTTP server and opens the browser.

Example:

```text
http://127.0.0.1:53682/
```

The flow is then:

```text
rclone
  ↓
browser
  ↓
Google login
  ↓
OAuth authorization
  ↓
return to http://127.0.0.1:53682/
  ↓
rclone retrieves OAuth code
```

Normal messages:

```text
NOTICE: Waiting for code...
NOTICE: Got code
```

---

## 13. Redirect URL

With a custom OAuth client, rclone may display:

```text
Make sure your Redirect URL is set to "http://127.0.0.1:53682/" in your custom config.
```

For a `Desktop app` type client, this local URL is used by rclone to retrieve the authentication result.

---

## 14. Error 403 — unauthorized user

Possible error:

```text
Access denied: rclone did not complete Google validation procedure
Error 403: access_denied
```

If the application is in test mode, check:

```text
Google Auth Platform
→ Audience
→ Test users
```

and add the Google account used for authentication.

Example:

```text
my.account@gmail.com
```

Then retry rclone authentication.

---

## 15. Shared Drive

rclone then asks:

```text
Configure this as a Shared Drive (Team Drive)?
```

For a personal Google Drive, answer:

```text
n
```

Shared Drives mainly concern Google Workspace.

---

## 16. Validate the remote

rclone then displays something like:

```text
Keep this "gdrive-personal" remote?

y) Yes this is OK
e) Edit this remote
d) Delete this remote
```

Answer:

```text
y
```

The remote is then registered in the rclone configuration.

---

## 17. Verify access works

Test the remote with:

```bash
rclone lsd "gdrive-personal:"
```

If the configuration is correct, rclone should display the folders at the root of the Google Drive.

Example:

```text
          -1 2026-09-07 15:00:00        -1 Documents
          -1 2026-09-07 15:00:00        -1 Photos
          -1 2026-09-07 15:00:00        -1 DriveSync
```

At this point:

```text
OAuth                ✅
Client ID            ✅
Client Secret        ✅
Test user            ✅
Google Drive API     ✅
rclone remote        ✅
Google Drive access  ✅
```

---

# Useful checks

## Display configured remotes

```bash
rclone listremotes
```

---

## Display configuration masking secrets

```bash
rclone config redacted "gdrive-personal"
```

---

## Display the path to the rclone configuration file

```bash
rclone config file
```

---

# Security

DriveSync must never manage directly:

- the Google password;
- the OAuth Access Token;
- the OAuth Refresh Token;
- the Client Secret in its own configuration.

This information remains the responsibility of `rclone`.

DriveSync should only know the name of the remote used.

Example:

```ini
[drive]
remote = gdrive-personal
root = DriveSync
```

---

# Chosen architecture

```text
DriveSync
    │
    ├── directory configuration
    ├── status
    ├── check
    ├── orchestration
    │
    ▼
rclone
    │
    ├── Google OAuth
    ├── tokens
    ├── Google Drive API
    ├── bisync
    ├── conflicts
    ├── recovery
    └── logs
```

Principle:

> DriveSync never reimplements a feature already correctly provided by rclone.

---

# Next step

Once authentication is validated, do not start directly with `~/Documents`.

First create a small test directory, for example:

```bash
mkdir -p ~/DriveSync-Test
```

Then use this folder to validate:

- local creation → Google Drive;
- Google Drive creation → local;
- local modification;
- remote modification;
- deletion;
- conflict;
- offline operation;
- recovery after reconnection.

Once these tests are validated, synchronization of `~/Documents` can be configured.
