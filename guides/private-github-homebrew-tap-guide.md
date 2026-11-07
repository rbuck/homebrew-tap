# Installing Private GitHub Release Assets via Homebrew

## Overview

**n.b. it is frequently the case, herein, that `<app-name>` == `<repo>`**

Homebrew cannot download release binaries from private GitHub repositories using standard web release URLs (`github.com/<owner>/<repo>/releases/download/<tag>/<asset>`), because unauthenticated `curl` requests receive an `HTTP 404` error. Additionally, Homebrew's strict AST parser blocks custom Ruby download strategy classes inside formula files, and its `superenv` sandbox strips environment variables unless prefixed with `HOMEBREW_`.

To distribute and install private release assets (such as `<owner>/<repo>`) cleanly without custom Ruby download strategies:
1. Query the GitHub REST API to retrieve the numeric **Asset ID** for each release binary.
2. Point the Homebrew formula `url` to `api.github.com/repos/<owner>/<repo>/releases/assets/<asset_id>` with the `Accept: application/octet-stream` header.
3. Authenticate using `HOMEBREW_GITHUB_API_TOKEN`, which Homebrew preserves inside its sandbox.

---

## Step 1: Retrieve the Release Asset ID

Each uploaded asset in a GitHub Release is assigned a unique numeric database ID. Use the GitHub CLI (`gh`) to list the assets and their IDs for a specific release tag:

```bash
gh api "repos/<owner>/<repo>/releases/tags/v1.2.4" --jq '.assets[] | {id: .id, name: .name, api_url: .url}'
```

For example, retrieve asset metadata with `curl`:

```bash
curl -L \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $(gh auth token)" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/<owner>/<repo>/releases/assets/<asset_id>"
```

### Example Output
```json
{
  "api_url": "https://api.github.com/repos/<owner>/<repo>/releases/assets/1234567890",
  "id": 719246964,
  "name": "<app-name>-1.2.3-aarch64-apple-darwin.tar.gz"
}
```

*(Note: Every new release or re-uploaded asset receives a new numeric `id`, so this lookup must be performed after uploading release binaries.)*

---

## Step 2: Verify the Download and Compute SHA-256

Before editing the Homebrew formula, verify that the API endpoint streams the binary archive (rather than JSON metadata or an HTTP error) and calculate its SHA-256 checksum:

```bash
curl -fL \
  -H "Accept: application/octet-stream" \
  -H "Authorization: Bearer $(gh auth token)" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/<owner>/<repo>/releases/assets/<asset_id>" \
  -o <app-name>-1.2.4-aarch64-apple-darwin.tar.gz && \
  file <app-name>-1.2.4-aarch64-apple-darwin.tar.gz && \
  shasum -a 256 <app-name>-1.2.4-aarch64-apple-darwin.tar.gz
```

* **`file` output** should confirm: `gzip compressed data`.
* **`shasum` output** provides the 64-character hash needed for the formula's `sha256` field.
* To inspect the packaged files, run `tar -tzf <app-name>-1.2.4-aarch64-apple-darwin.tar.gz`.

---

## Step 3: Configure the Homebrew Formula (`Formula/<app-name>.rb`)

Use Homebrew's built-in `url` and `headers:` DSL directly inside your formula—no custom Ruby classes or `lib/` files are required:

```ruby
class AppName < Formula
  desc "AppName"
  homepage "https://github.com/<owner>/<repo>"
  version "1.2.4"

  on_macos do
    if Hardware::CPU.arm?
      url "https://api.github.com/repos/<owner>/<repo>/releases/assets/<asset_id>",
          headers: [
            "Accept: application/octet-stream",
            "Authorization: Bearer #{ENV.fetch("HOMEBREW_GITHUB_API_TOKEN")}",
            "X-GitHub-Api-Version: 2022-11-28"
          ]
      sha256 "REPLACE_WITH_64_CHAR_SHA256_FROM_STEP_2"
    end
  end

  def install
    bin.install "<app-name>"
  end
end
```

### Handling Extensionless API URLs (If Auto-Extraction Fails)
Because `.../releases/assets/<asset_id>` does not end in `.tar.gz`, some Homebrew versions may stage the downloaded file without unpacking it. If `bin.install "<app-name>"` fails because the archive was not extracted automatically, unpack `cached_download` explicitly inside `def install`:

```ruby
  def install
    system "tar", "-xzf", cached_download, "--strip-components=1"
    bin.install "<app-name>"
  end
```

---

## Step 4: Install or Upgrade via Homebrew

Export `HOMEBREW_GITHUB_API_TOKEN` when running `brew install` or `brew upgrade`. Because the variable name begins with `HOMEBREW_`, Homebrew passes it through its sandbox into the formula's `ENV`:

```bash
HOMEBREW_GITHUB_API_TOKEN=$(gh auth token) brew install --verbose <owner>/tap/<repo>
```

*(Tip: To avoid passing the token manually every time, add `export HOMEBREW_GITHUB_API_TOKEN="$(gh auth token)"` to your `~/.zshrc` or `~/.bashrc`—or set a dedicated read-only GitHub Personal Access Token with `repo` scope.)*

### Diagnose an installation

Reinstall with verbose output, locate the installed CLI, check that it starts, and run the formula test:

```bash
HOMEBREW_GITHUB_API_TOKEN="$(gh auth token)" brew reinstall --verbose <owner>/tap/<app-name>
which your-app
your-app --help
HOMEBREW_GITHUB_API_TOKEN="$(gh auth token)" brew test --verbose <owner>/tap/<app-name>
```

---

## Step 5: Automating Updates in GitHub Actions (CI)

If you publish releases via CI (such as `cargo-dist` or a custom release workflow), update the formula **after** uploading the release assets:

1. Upload the `.tar.gz` binary to the GitHub Release.
2. Query the GitHub API for the newly generated asset ID:
   ```bash
   ASSET_ID=$(gh api "repos/<owner>/<repo>/releases/tags/${TAG}" \
     --jq '.assets[] | select(.name == "tool-'"${VERSION}"'-aarch64-apple-darwin.tar.gz") | .id')
   ```
3. Compute the `sha256sum` of the tarball.
4. Render `Formula/<app-name>.rb` with the new `ASSET_ID` and `SHA256`, then commit and push it to your tap repository.

For example, when updating from v1.2.3 to v1.2.4, use `TAG=v1.2.4` and `VERSION=1.2.4`.

---

## Troubleshooting

| Symptom / Error | Cause | Fix |
| :--- | :--- | :--- |
| `curl: (56) ... error: 404` | Using `github.com/.../releases/download/...` on a private repo | Switch the formula `url` to `api.github.com/repos/<owner>/<repo>/releases/assets/<id>`. |
| `curl: (56) ... error: 406` | Sending `Accept: application/octet-stream` to `github.com` instead of `api.github.com` | Ensure the URL starts with `https://api.github.com/repos/...`. |
| `KeyError: key not found: "HOMEBREW_GITHUB_API_TOKEN"` | Token variable was not set or lacked the `HOMEBREW_` prefix | Run `HOMEBREW_GITHUB_API_TOKEN=$(gh auth token) brew install ...`. |
| `Error: Fetching /opt/homebrew/Library/Taps/<user>/<tap> failed!` | `brew untap` fails when a remote tap repo is private or deleted | Force-remove with `brew untap --force <user>/<tap>` or `rm -rf /opt/homebrew/Library/Taps/<user>/<tap>`. |
