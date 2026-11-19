# PELDRUN Provider Template

A complete, production-ready repository template for creating, building, testing, and publishing a new **LLM provider package** for PELDRUN.

This template contains all the structural files, automation scripts, and CI/CD workflows required by the PELDRUN Provider Package ecosystem. It is modeled directly on the official [Provider Package Repository guide](https://github.com/peldrun/peldrun/blob/main/docs/providers/Provider%20Package%20Repository.md) and the reference implementation [`peldrun-provider-cloudflare-ai`](https://github.com/peldrunai/peldrun-provider-cloudflare-ai).

You only need to implement two provider-specific files (`manifest.json` and `adapter.py`). Everything else — packaging, verification, versioning, changelog generation, catalog metadata, and releases — is fully automated.

---

## Table of Contents

1. [Overview](#1-overview)
2. [What This Template Provides](#2-what-this-template-provides)
3. [Repository Architecture](#3-repository-architecture)
4. [Requirements](#4-requirements)
5. [Quick Start](#5-quick-start)
6. [The Bootstrap Script](#6-the-bootstrap-script)
   - [6.1 What It Does](#61-what-it-does)
   - [6.2 CLI Reference](#62-cli-reference)
   - [6.3 Naming Derivations](#63-naming-derivations)
   - [6.4 Placeholder Reference](#64-placeholder-reference)
   - [6.5 Legacy Literal Normalization](#65-legacy-literal-normalization)
   - [6.6 Safety Guarantees](#66-safety-guarantees)
   - [6.7 Dry Run](#67-dry-run)
   - [6.8 Idempotency](#68-idempotency)
   - [6.9 Exit Codes](#69-exit-codes)
7. [Provider-Specific Files You Must Implement](#7-provider-specific-files-you-must-implement)
   - [7.1 manifest.json](#71-manifestjson)
   - [7.2 adapter.py](#72-adapterpy)
   - [7.3 requirements.txt](#73-requirementstxt)
8. [The Six Automation Scripts](#8-the-six-automation-scripts)
   - [8.1 validate_manifest.py](#81-validate_manifestpy)
   - [8.2 update_version.py](#82-update_versionpy)
   - [8.3 changelog.py](#83-changelogpy)
   - [8.4 build_package.py](#84-build_packagepy)
   - [8.5 verify_package.py](#85-verify_packagepy)
   - [8.6 generate_catalog_entry.py](#86-generate_catalog_entrypy)
9. [CI/CD Workflows](#9-cicd-workflows)
   - [9.1 validate.yml](#91-validateyml)
   - [9.2 release.yml](#92-releaseyml)
10. [Development Lifecycle](#10-development-lifecycle)
11. [Building a Release Manually](#11-building-a-release-manually)
12. [Publishing to the Catalog](#12-publishing-to-the-catalog)
13. [Package Layout and Reproducible Builds](#13-package-layout-and-reproducible-builds)
14. [Security Model](#14-security-model)
15. [Testing](#15-testing)
16. [Version Management](#16-version-management)
17. [Troubleshooting](#17-troubleshooting)
18. [FAQ](#18-faq)
19. [License](#19-license)

---

## 1. Overview

PELDRUN runs the core agent logic. **Provider Packages** are standalone repositories that contain the adapter code, the manifest, and the automation scripts required to package and distribute a provider.

Every provider repository (Cloudflare, GigaChat, OpenAI, etc.) shares the exact same structural DNA. This template encodes that structure so that:

- GitHub Actions can reliably find and process your code.
- The local build scripts produce a deterministic, installable `.zip`.
- The PELDRUN backend can validate, install, and run your provider inside an isolated virtualenv.

The template is **generic**: the automation scripts read all provider-specific data dynamically from `manifest.json`. You never edit the scripts themselves.

---

## 2. What This Template Provides

| Component | Purpose |
|-----------|---------|
| `scripts/bootstrap_provider.py` | One-time initializer that replaces all placeholders and renames directories automatically. |
| `scripts/validate_manifest.py` | Static validation of `manifest.json` (stdlib-only). |
| `scripts/update_version.py` | Single source of truth for version bumping across all files. |
| `scripts/changelog.py` | Generates release notes from Conventional Commits. |
| `scripts/build_package.py` | Builds a deterministic, reproducible `.zip` artifact. |
| `scripts/verify_package.py` | Mirrors PELDRUN's install-time security checks. |
| `scripts/generate_catalog_entry.py` | Produces `catalog-entry.json` for the PELDRUN Store. |
| `.github/workflows/validate.yml` | CI on every push / pull request. |
| `.github/workflows/release.yml` | CI on every `v*` tag; publishes a GitHub Release. |
| `pyproject.toml` | Local development install and tool configuration. |
| `tests/test_manifest.py` | Manifest integrity tests. |
| `.gitignore`, `LICENSE`, `CHANGELOG.md`, `README.md` | Standard repository scaffolding. |

What this template **does not** provide (because they differ per provider):

- `manifest.json` — you declare your provider's identity, connection fields, features, and permissions.
- `src/<package>/adapter.py` — you implement the actual API communication.
- `requirements.txt` — you list your provider's runtime dependencies.

---

## 3. Repository Architecture

Every PELDRUN provider repository follows this exact layout:

```text
peldrun-provider-<id>/
│
├── .github/
│   └── workflows/
│       ├── validate.yml          # CI: runs on push / PR
│       └── release.yml           # CI: runs on v* tags
│
├── dist/                         # Build artifacts (ZIP, JSON) — GITIGNORED
│
├── scripts/                      # Automation scripts (stdlib-only)
│   ├── bootstrap_provider.py     # One-time initializer (gitignored after use)
│   ├── build_package.py
│   ├── changelog.py
│   ├── generate_catalog_entry.py
│   ├── update_version.py
│   ├── validate_manifest.py
│   └── verify_package.py
│
├── src/
│   └── <id_snake>_peldrun/       # The Python package
│       ├── __init__.py
│       ├── adapter.py            # Implement your provider logic here
│       └── py.typed
│
├── tests/
│   └── test_manifest.py          # Integrity tests
│
├── .gitignore
├── CHANGELOG.md
├── LICENSE
├── manifest.json                 # Implement your provider declaration here
├── pyproject.toml
├── README.md
└── requirements.txt
```

> **Important:** The `src/` directory is flattened at build time. Inside the final ZIP, the package lives at `<id_snake>_peldrun/`, **not** at `src/<id_snake>_peldrun/`. This is required so the `entry_point` in the manifest resolves correctly.

---

## 4. Requirements

- **Python 3.12.x** — matches `manifest.runtime.python` and `pyproject.toml` (`>=3.12,<3.13`). Other versions are rejected at install time.
- **pip**
- **git** — required by the changelog script to read commit history.

All automation scripts are **stdlib-only**. They run in a bare CI environment without PELDRUN, pydantic, or any third-party package installed.

---

## 5. Quick Start

### Step 1 — Create your repository from this template

Clone or copy the template, then enter the directory:

```bash
git clone <your-template-url> peldrun-provider-my-provider
cd peldrun-provider-my-provider
```

### Step 2 — Preview the initialization (recommended)

```bash
python scripts/bootstrap_provider.py --id my-provider --dry-run
```

This prints every change that would be made **without writing anything**.

### Step 3 — Initialize the repository

```bash
python scripts/bootstrap_provider.py \
    --id my-provider \
    --display-name "My Provider AI" \
    --author "Your Name" \
    --author-url "https://github.com/yourname" \
    --homepage-url "https://my-provider.example.com" \
    --brand-color "#F38020" \
    --icon myprovider
```

Or minimal (auto-derives display name, class name, and icon):

```bash
python scripts/bootstrap_provider.py --id my-provider
```

The bootstrap script will:

- Replace every placeholder across all files.
- Rename `src/{{PROVIDER_ID_SNAKE}}_peldrun/` to `src/my_provider_peldrun/`.
- Normalize legacy hardcoded literals (brand color, icon, author) automatically.
- Fix the `CHANGE_ME_peldrun` stub path in `update_version.py`.
- Add itself to `.gitignore`.

### Step 4 — Implement your provider

Fill in:

- `manifest.json`
- `src/my_provider_peldrun/adapter.py`
- `requirements.txt`

### Step 5 — Validate, build, and verify

```bash
python scripts/validate_manifest.py
python scripts/build_package.py
python scripts/verify_package.py
python -m pytest tests -v
```

### Step 6 — Release

```bash
python scripts/update_version.py patch
git add -A
git commit -m "feat: initial provider implementation"
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin main --tags
```

The `release.yml` workflow takes over from here: it builds the ZIP, generates the catalog entry, and creates a GitHub Release automatically.

---

## 6. The Bootstrap Script

`scripts/bootstrap_provider.py` is a **one-time template initializer**. It converts the generic template into a concrete provider repository.

### 6.1 What It Does

1. **Validates** the provider ID against PELDRUN's manifest rules.
2. **Derives** every naming variant (snake_case, PascalCase, display name).
3. **Normalizes** legacy hardcoded literals into canonical placeholders.
4. **Replaces** every `{{PLACEHOLDER}}` token across all text files.
5. **Renames** directories whose names contain placeholders (deepest first).
6. **Excludes itself** from version control by appending to `.gitignore`.
7. **Scans** for any unresolved placeholders and reports them.

### 6.2 CLI Reference

```text
python scripts/bootstrap_provider.py --id <provider-id> [options]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--id` | Yes | — | Provider ID. Lowercase, e.g. `my-provider`. Automatically lowercased and trimmed. |
| `--display-name` | No | Derived from `--id` | Human-friendly name shown in the Store. |
| `--author` | No | `PELDRUN Community` | Author name for the manifest and pyproject. |
| `--author-url` | No | `""` | Author profile URL. |
| `--homepage-url` | No | `""` | Provider homepage URL. |
| `--icon` | No | snake_case ID | Store icon slug. Must be lowercase. |
| `--brand-color` | No | `#000000` | Hex brand color, e.g. `#F38020`. |
| `--dry-run` | No | `false` | Preview all changes without writing anything. |

### 6.3 Naming Derivations

Given `--id cloudflare-ai`:

| Variant | Value | Rule |
|---------|-------|------|
| Provider ID | `cloudflare-ai` | Canonical input (lowercased). |
| Snake case | `cloudflare_ai` | Replace `-` and `.` with `_`. |
| Package name | `cloudflare_ai_peldrun` | `<snake>_peldrun`. |
| Class name | `CloudflareAi` | Capitalize each snake segment. |
| Adapter class | `CloudflareAiAdapter` | `<ClassName>Adapter`. |
| Entry point | `cloudflare_ai_peldrun.adapter:CloudflareAiAdapter` | `<package>.adapter:<ClassName>Adapter`. |
| Display name (auto) | `Cloudflare AI` | Title case with acronym preservation. |

When `--display-name` is omitted, the script auto-derives it and preserves common acronyms:

| Word | Rendered |
|------|----------|
| `ai` | `AI` |
| `api` | `API` |
| `llm` | `LLM` |
| `gpt` | `GPT` |
| `ml` | `ML` |

Example: `--id my-cool-llm` → display name `My Cool LLM`.

### 6.4 Placeholder Reference

The bootstrap script replaces the following tokens:

| Token | Replaced With |
|-------|---------------|
| `{{PROVIDER_ID}}` | Canonical provider ID. |
| `{{PROVIDER_ID_SNAKE}}` | snake_case variant. |
| `{{PROVIDER_DISPLAY_NAME}}` | Display name. |
| `{{PROVIDER_NAME}}` | Display name (alias). |
| `{{ProviderClassName}}` | PascalCase class name (without `Adapter` suffix). |
| `{{AUTHOR_NAME}}` | `--author` value. |
| `{{AUTHOR_URL}}` | `--author-url` value. |
| `{{HOMEPAGE_URL}}` | `--homepage-url` value. |
| `{{ICON_NAME}}` | `--icon` value, or snake_case ID. |
| `{{BRAND_COLOR}}` | `--brand-color` value. |
| `CHANGE_ME_peldrun` | `<snake>_peldrun` (fixes the stub in `update_version.py`). |

Tokens are replaced **longest-first** to avoid partial collisions (e.g., `{{PROVIDER_ID}}` never corrupts `{{PROVIDER_ID_SNAKE}}`).

### 6.5 Legacy Literal Normalization

Some template revisions ship **concrete default values** instead of placeholders in a few tooling files. The bootstrap script automatically upgrades these literals to canonical placeholders **before** the main replacement pass, so you never need to edit them manually.

This is handled by the `LEGACY_LITERAL_PATCHES` table and the `normalize_legacy_literals()` function inside `bootstrap_provider.py`.

#### Patch 1 — Brand color in `release.yml`

File: `.github/workflows/release.yml` (inside the `Generate catalog entry` step)

Before:

```yaml
--brand-color "#000000"
```

Normalized to:

```yaml
--brand-color "{{BRAND_COLOR}}"
```

Then replaced with your `--brand-color` value, e.g.:

```yaml
--brand-color "#F38020"
```

#### Patch 2 — Icon in `release.yml`

File: `.github/workflows/release.yml` (same step)

Before:

```yaml
--icon default
```

Normalized to:

```yaml
--icon {{ICON_NAME}}
```

Then replaced with your `--icon` value, e.g.:

```yaml
--icon cloudflare
```

#### Patch 3 — Author in `pyproject.toml`

File: `pyproject.toml` (inside the `[project]` section)

Before:

```toml
authors = [{ name = "Your Name" }]
```

Normalized to:

```toml
authors = [{ name = "{{AUTHOR_NAME}}" }]
```

Then replaced with your `--author` value, e.g.:

```toml
authors = [{ name = "PELDRUN Community" }]
```

#### Resulting `release.yml` step

After running the bootstrap with `--id cloudflare-ai --brand-color "#F38020" --icon cloudflare`:

```yaml
- name: Generate catalog entry
  run: |
    VERSION=$(python -c "import json; print(json.load(open('manifest.json'))['version'])")
    URL="https://github.com/${{ github.repository }}/releases/download/${{ steps.tag.outputs.tag }}/cloudflare-ai-${VERSION}.zip"
    python scripts/generate_catalog_entry.py \
      --download-url "$URL" \
      --brand-color "#F38020" \
      --icon cloudflare
```

> **Note:** The patterns are intentionally conservative. They only match untouched template defaults (`"#000000"`, `default`, `"Your Name"`). Values you have already customized by hand are preserved.

### 6.6 Safety Guarantees

The bootstrap script is designed to be safe and predictable:

- **Stdlib-only** — no third-party dependencies.
- **Preserves line endings** — reads and writes raw bytes; never converts LF to CRLF.
- **JSON-escapes values** — when writing into `.json` files, values containing quotes or backslashes are escaped so the file stays valid JSON.
- **Skips binary files** — any file that is not valid UTF-8 is ignored.
- **Never rewrites itself** — the script's own replacement map is excluded from scanning.
- **Prunes ignored directories** — `.git`, `dist`, `build`, `__pycache__`, `.venv`, `venv`, `.tox`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `node_modules`, `.idea`, `.vscode`.
- **Skips large files** — files larger than 2 MB are treated as assets.
- **Preserves GitHub Actions expressions** — expressions like `${{ github.repository }}` are untouched because they contain spaces or dots that do not match the placeholder pattern.
- **Validates inputs** — rejects invalid IDs, built-in adapter collisions, malformed hex colors, non-slug icons, and values containing line breaks.

#### Provider ID validation

The ID must match:

```text
^[a-z0-9][a-z0-9._-]*$
```

The following IDs are **reserved** by PELDRUN's built-in adapters and are rejected:

```text
openai_compat, lmstudio, ollama, openai_native,
anthropic, google_genai, ollama_native, lmstudio_native
```

### 6.7 Dry Run

Always preview before writing:

```bash
python scripts/bootstrap_provider.py --id my-provider --dry-run
```

Example output:

```text
PELDRUN provider bootstrap
  id:           my-provider
  package:      my_provider_peldrun
  adapter:      MyProviderAdapter
  display name: My Provider
  mode:         dry-run (no writes)

  [dry] CHANGELOG.md (1 replacement)
  [dry] LICENSE (1 replacement)
  [dry] README.md (2 replacements)
  [dry] manifest.json (9 replacements)
  [dry] pyproject.toml (3 replacements)
  [dry] .github/workflows/release.yml (3 replacements)
  [dry] scripts/update_version.py (1 replacement)
  [dry] src/{{PROVIDER_ID_SNAKE}}_peldrun/__init__.py (2 replacements)
  [dry] src/{{PROVIDER_ID_SNAKE}}_peldrun/adapter.py (2 replacements)
  [dry] renamed src/{{PROVIDER_ID_SNAKE}}_peldrun -> src/my_provider_peldrun

Done: 9 file(s) updated, 24 replacement(s), 1 directory rename(s).
```

No files are modified and no directories are renamed in dry-run mode.

### 6.8 Idempotency

The script is safe to re-run. Files that no longer contain placeholders are left untouched. A second run reports:

```text
Done: 0 file(s) updated, 0 replacement(s), 0 directory rename(s).
```

This also holds when a legacy literal normalizes back to the same value (e.g., running with the default `--brand-color "#000000"`).

### 6.9 Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success. |
| `1` | Invalid arguments, or unresolved placeholders remain after the run. |
| `2` | Filesystem error (could not read or write a file). |

---

## 7. Provider-Specific Files You Must Implement

These files differ for every provider. The template leaves them for you to complete.

### 7.1 manifest.json

The core definition file. It declares identity, transport, entry point, permissions, and connection fields.

Required fields:

| Field | Description |
|-------|-------------|
| `schema_version` | Must be `1.0.0`. |
| `kind` | Must be `peldrun.llm_provider`. |
| `id` | Lowercase provider ID matching `^[a-z0-9][a-z0-9._-]*$`. |
| `name` | Non-empty display name. |
| `version` | Valid SemVer, e.g. `0.1.0`. |
| `api_contract` | Must be `peldrun.llm.provider.v1`. |
| `transport` | One of `compatible`, `native`, `custom`. |
| `permissions` | See below. |

Transport rules:

- `native` / `custom` → must declare `entry_point` (`module:ClassName`), must **not** declare `base_adapter`.
- `compatible` → must declare `base_adapter`, must **not** declare `entry_point`.

Permission rules (enforced by `validate_manifest.py` and `verify_package.py`):

```json
{
  "network": "connection_endpoint",
  "secrets": ["connection.api_key"],
  "workspace_access": false,
  "shell_execute": false
}
```

- `workspace_access` must be explicitly `false`.
- `shell_execute` must be explicitly `false`.
- `network` must be `none` or `connection_endpoint`.
- `secrets` entries must be `connection.api_key`.

Minimal example:

```json
{
  "schema_version": "1.0.0",
  "kind": "peldrun.llm_provider",
  "id": "my-provider",
  "name": "My Provider AI",
  "display_name": "My Provider",
  "version": "0.1.0",
  "description": "Short description of the provider.",
  "api_contract": "peldrun.llm.provider.v1",
  "transport": "native",
  "entry_point": "my_provider_peldrun.adapter:MyProviderAdapter",
  "dependencies": ["httpx>=0.27,<0.28"],
  "runtime": { "type": "python", "python": ">=3.12,<3.13" },
  "author": "Your Name",
  "license": "MIT",
  "icon": "myprovider",
  "connection_fields": [
    {
      "key": "api_key",
      "label": "API Key",
      "type": "password",
      "required": true,
      "description": "Your provider API key."
    }
  ],
  "features": {
    "model_discovery": true,
    "native_streaming": true,
    "buffered_streaming": true,
    "tool_calling": false,
    "vision": false,
    "usage_reporting": true
  },
  "permissions": {
    "network": "connection_endpoint",
    "secrets": ["connection.api_key"],
    "workspace_access": false,
    "shell_execute": false
  }
}
```

### 7.2 adapter.py

Located at `src/<id_snake>_peldrun/adapter.py`. This is where you implement the actual communication with your provider's API.

A native adapter typically implements:

| Method | Purpose |
|--------|---------|
| `__init__` | Accept a `ConnectionContext` (or a factory `context`), extract credentials, build the HTTP client. |
| `generate(request)` | Non-streaming chat completion → returns `LLMResponse`. |
| `stream(request)` | Streaming chat completion → yields `LLMStreamEvent`. |
| `discover_models()` | Return the list of available models. |
| `validate_connection()` | Cheap ping (e.g. list models) → returns `{ok, message, latency_ms}`. Never raises. |
| `get_model_metadata(model_id)` | Return metadata for one model, or `None`. |
| `close()` | Release HTTP clients. Idempotent, never raises. |

The adapter imports from PELDRUN's contracts:

```python
from peldrun.llm.contracts import (
    AdapterFeatures,
    AdapterProfile,
    ConnectionContext,
    LLMStreamEvent,
    StreamEventType,
)
from peldrun.llm.request import LLMRequest
from peldrun.llm.client import LLMResponse
from peldrun.llm.errors import ProviderAuthError, ProviderError
```

> **Note:** `peldrun` is not installed during local development or CI type-checking. It lives inside the plugin host virtualenv at runtime. All imports from it are treated as `Any` by mypy.

### 7.3 requirements.txt

The isolated dependencies for this provider.

> **Critical:** Version pins **must** align with PELDRUN's own backend pins. The isolated venv created by `DependencyInstaller` installs `peldrun` transitively, which brings its own requirements. Mismatched pins cause pip resolver conflicts at install time.

Example (aligned with the reference implementation):

```text
openai>=2.50.0,<3.0.0
httpx>=0.27,<0.28
```

The `dependencies` array in `manifest.json` and the `dependencies` list in `pyproject.toml` must mirror `requirements.txt` verbatim.

---

## 8. The Six Automation Scripts

These scripts are the engine of the repository. They guarantee that every release is consistent, secure, and ready for the PELDRUN Store. They are entirely stdlib-only and read all provider-specific data from `manifest.json`.

### 8.1 validate_manifest.py

**Purpose:** Static analysis of `manifest.json`. Catches typos, missing fields, invalid SemVer, and unsafe permissions before you commit.

Checks performed:

1. JSON parses cleanly.
2. Required identity fields are present and typed.
3. Patterns: `id`, `version`, `entry_point`, `base_adapter`.
4. Transport consistency: `entry_point` XOR `base_adapter`.
5. Permissions: `workspace_access=false`, `shell_execute=false`, valid `network` and `secrets`.
6. No built-in adapter ID collision.
7. Dependencies are non-empty strings.
8. Entry-point module resolves to a real `.py` file under `src/`.
9. Optional: if `peldrun` is importable, runs the real `ProviderManifest` Pydantic model as an extra layer.

Usage:

```bash
python scripts/validate_manifest.py
python scripts/validate_manifest.py path/to/manifest.json
```

Exit codes: `0` valid, `1` validation failed, `2` manifest missing or invalid JSON.

### 8.2 update_version.py

**Purpose:** The single source of truth for version bumping. You **never** manually edit version numbers.

Updates:

- `manifest.json`
- `pyproject.toml`
- `src/<package>/__init__.py`
- Prepends a new section to `CHANGELOG.md`

Usage:

```bash
python scripts/update_version.py patch      # 0.1.0 -> 0.1.1
python scripts/update_version.py minor      # 0.1.0 -> 0.2.0
python scripts/update_version.py major      # 0.1.0 -> 1.0.0
python scripts/update_version.py 1.2.3      # explicit version
python scripts/update_version.py --check    # verify all files agree
```

The `--check` flag is used in CI to ensure version consistency across all files.

### 8.3 changelog.py

**Purpose:** Automatically generates release notes by parsing Git commit history since the last tag, looking for **Conventional Commits**.

Commit classification:

| Prefix | Category |
|--------|----------|
| `feat:` | Added |
| `fix:` | Fixed |
| `refactor:` | Changed |
| `perf:` | Changed |
| `chore:` | Changed (or skipped depending on configuration) |
| `docs:`, `test:`, `ci:`, `style:` | Skipped |

Usage:

```bash
python scripts/changelog.py 0.2.0
```

Output is Keep-a-Changelog compatible Markdown.

### 8.4 build_package.py

**Purpose:** Creates the final `.zip` artifact.

Crucial behaviors:

- Places `manifest.json` and `requirements.txt` at the archive root.
- **Flattens** `src/<package>/` into `<package>/` at the root.
- Sets **deterministic timestamps** (`2020-01-01 00:00:00`) on every entry.
- Sets standard file permissions (`0o644`).
- Excludes `__pycache__` and other junk.

This ensures the resulting ZIP always has the **exact same SHA-256 hash** if the source code has not changed (reproducible builds).

Usage:

```bash
python scripts/build_package.py
python scripts/build_package.py --verify   # build + sanity check
```

Output: `dist/<id>-<version>.zip`

### 8.5 verify_package.py

**Purpose:** Simulates PELDRUN's strict install-time security checks before you upload the package.

Checks:

1. File exists and is a valid ZIP.
2. Compressed size ≤ 100 MB.
3. Uncompressed size ≤ 500 MB.
4. Compression ratio ≤ 100:1.
5. File count ≤ 2000.
6. Path safety per entry: no NUL, no backslash, no absolute path, no Windows drive letter, no `..` traversal, no empty interior segment, path length ≤ 1024.
7. Symlink rejection (`S_IFLNK` in `external_attr`).
8. `manifest.json` present at the archive root.
9. Manifest is valid JSON and passes basic schema validation.
10. `entry_point` resolves to a real `.py` file inside the archive.
11. `requirements.txt` present at the root for native/custom transports.
12. Computes and prints the SHA-256 checksum.
13. Optional: `--expected-sha256` compares against a recorded hash to detect non-reproducible builds.

Usage:

```bash
python scripts/verify_package.py
python scripts/verify_package.py dist/my-provider-0.1.0.zip
python scripts/verify_package.py dist/my-provider-0.1.0.zip --expected-sha256 <hash>
```

When no path is given, it auto-discovers the most recently modified `dist/*.zip`.

Exit codes: `0` valid, `1` failed checks, `2` file not found / not a readable ZIP.

> **Save the printed SHA-256.** It is used as `checksum_sha256` in the catalog entry.

### 8.6 generate_catalog_entry.py

**Purpose:** Generates `catalog-entry.json`. This file is **NOT** part of the ZIP. It is the metadata file used by the PELDRUN Store to display the provider, its brand color, and its download URL.

Usage:

```bash
python scripts/generate_catalog_entry.py \
    --download-url "https://github.com/<owner>/<repo>/releases/download/v0.1.0/my-provider-0.1.0.zip" \
    --brand-color "#F38020" \
    --icon myprovider
```

The entry includes:

- `id`, `name`, `version`, `transport`
- `features`, `permissions`
- `brand_color`, `icon`, `icon_type`
- `download_url`
- `checksum_sha256`
- `developer` block derived from the manifest author

Output: `dist/catalog-entry.json`

---

## 9. CI/CD Workflows

### 9.1 validate.yml

Runs on every push to `main` and every pull request. It ensures the manifest is valid, versions are consistent, the package builds, and tests pass.

Pipeline:

1. Checkout (full history for `git describe`).
2. Setup Python 3.12.
3. Install `requirements.txt` + `pytest`.
4. `python scripts/validate_manifest.py`
5. `python scripts/update_version.py --check`
6. `python scripts/build_package.py`
7. `python scripts/verify_package.py`
8. `python -m pytest tests -v`
9. Upload the built ZIP as a workflow artifact (useful for PR reviewers).

### 9.2 release.yml

Runs only when you push a `v*` tag (e.g. `v1.0.0`). It builds the ZIP, generates the catalog entry, and creates a GitHub Release automatically.

Pipeline:

1. Checkout (full history).
2. Setup Python 3.12.
3. Install dependencies.
4. Validate manifest.
5. Verify version consistency.
6. Resolve the release tag.
7. **Verify the tag matches `manifest.json["version"]`** — aborts on mismatch.
8. Build the ZIP.
9. Verify the ZIP and extract the SHA-256.
10. Generate `catalog-entry.json` with the correct GitHub Release download URL.
11. Upload workflow artifacts.
12. Create a GitHub Release containing `dist/*.zip` and `dist/catalog-entry.json`.

> **Tag/manifest mismatch guard:** If the tag is `v1.2.3` but the manifest says `1.2.4`, the workflow fails before creating any release. Run `python scripts/update_version.py 1.2.3` locally and commit before tagging.

---

## 10. Development Lifecycle

The exact sequence of commands from a fresh template to a published release:

```bash
# 1. Initialize the template
python scripts/bootstrap_provider.py --id my-provider --display-name "My Provider AI"

# 2. Implement manifest.json, adapter.py, requirements.txt

# 3. Validate and test locally
python scripts/validate_manifest.py
python -m pytest tests -v

# 4. Bump the version and generate the changelog
python scripts/update_version.py minor

# 5. Build and verify
python scripts/build_package.py
python scripts/verify_package.py
# Note the SHA-256 hash printed at the end.

# 6. Commit and tag
git add -A
git commit -m "feat: add vision support"
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin main --tags

# 7. The release.yml workflow builds and publishes automatically.

# 8. Publish to the catalog (see Section 12).
```

---

## 11. Building a Release Manually

If you prefer to release without CI:

```bash
# 1. Bump the version everywhere and prepend a CHANGELOG section
python scripts/update_version.py patch

# 2. Review the generated CHANGELOG section
$EDITOR CHANGELOG.md

# 3. Build and verify the archive
python scripts/build_package.py --verify
python scripts/verify_package.py

# 4. Generate the catalog entry with the correct download URL
VERSION=$(python -c "import json; print(json.load(open('manifest.json'))['version'])")
python scripts/generate_catalog_entry.py \
    --download-url "https://github.com/<owner>/<repo>/releases/download/v${VERSION}/my-provider-${VERSION}.zip" \
    --brand-color "#F38020" \
    --icon myprovider

# 5. Commit and tag
git add -A
git commit -m "chore(release): v0.1.1"
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin main
git push origin v0.1.1
```

---

## 12. Publishing to the Catalog

After the GitHub Release is created:

1. Navigate to the `peldrun-provider-catalog` repository on GitHub.
2. Go to **Actions**.
3. Run the `import_catalog_entry.py` workflow with the URL of your new `catalog-entry.json`.

The catalog entry is attached to every GitHub Release by `release.yml`. Once imported, your provider appears in the PELDRUN Store **Catalog** tab after the next catalog refresh.

---

## 13. Package Layout and Reproducible Builds

The final ZIP produced by `build_package.py` has this layout:

```text
my-provider-0.1.0.zip
├── manifest.json              # copied from repo root
├── requirements.txt           # copied from repo root
└── my_provider_peldrun/       # src/my_provider_peldrun/, flattened
    ├── __init__.py
    ├── adapter.py
    └── py.typed
```

Reproducibility guarantees:

- Deterministic timestamps (`2020-01-01 00:00:00`).
- Deterministic file permissions (`0o644`).
- No `__pycache__`, no archiver junk (`__MACOSX`, `.DS_Store`, `Thumbs.db`).
- Sorted, stable entry ordering.

If the source code is unchanged, the SHA-256 hash is identical across builds and machines.

> The bootstrap script, tests, scripts, and workflows are **never** included in the ZIP. Only `manifest.json`, `requirements.txt`, and the flattened `src/` package are shipped.

---

## 14. Security Model

PELDRUN enforces strict security at install time. This template mirrors those checks locally so you catch problems before uploading.

| Check | Enforcement |
|-------|-------------|
| Path traversal (`..`) | Rejected by `verify_package.py`. |
| Absolute paths / Windows drive letters | Rejected. |
| Symlinks | Rejected (`S_IFLNK`). |
| NUL bytes / backslashes in paths | Rejected. |
| Compression bombs | Ratio capped at 100:1. |
| Oversized archives | Compressed ≤ 100 MB, uncompressed ≤ 500 MB. |
| File count | ≤ 2000. |
| Workspace access | Must be `false` in manifest. |
| Shell execution | Must be `false` in manifest. |
| Network scope | `none` or `connection_endpoint`. |
| Secrets scope | `connection.api_key` only. |

The adapter runs inside an **isolated virtualenv** created from `requirements.txt`. It never touches the PELDRUN workspace or shell.

---

## 15. Testing

Run the manifest integrity tests:

```bash
python -m pytest tests -v
```

The template ships `tests/test_manifest.py`, which verifies:

- `manifest.json` exists at the repository root.
- It is valid JSON.
- It contains the required `id` and `version` fields.

You can extend the test suite with adapter-level tests. Note that adapter tests require `peldrun` to be importable; CI installs only `pytest` and the runtime dependencies, so live adapter tests should be marked and skipped when `peldrun` is unavailable.

Development extras (never installed in the provider's isolated venv):

```bash
pip install -e ".[dev]"
```

This installs `pytest`, `pytest-asyncio`, and `ruff`.

---

## 16. Version Management

**Never edit version numbers by hand.** Always use:

```bash
python scripts/update_version.py <major|minor|patch|X.Y.Z>
```

This updates `manifest.json`, `pyproject.toml`, `__init__.py`, and `CHANGELOG.md` together.

To verify consistency (used in CI):

```bash
python scripts/update_version.py --check
```

The release tag must match the manifest version (without the leading `v`):

| Manifest version | Tag |
|------------------|-----|
| `0.1.0` | `v0.1.0` |
| `1.2.3` | `v1.2.3` |

---

## 17. Troubleshooting

### "Invalid provider ID"

The ID must match `^[a-z0-9][a-z0-9._-]*$`. Use lowercase letters, digits, hyphens, dots, or underscores. It must start with a letter or digit.

### "Provider ID collides with a built-in adapter"

Choose a different ID. Reserved IDs include `ollama`, `anthropic`, `openai_native`, `lmstudio`, `google_genai`, etc.

### "entry_point module does not resolve to a file in src/"

Ensure the `entry_point` in `manifest.json` matches your actual package and file layout. For `my_provider_peldrun.adapter:MyProviderAdapter`, the file `src/my_provider_peldrun/adapter.py` must exist.

### "permissions.workspace_access must be false"

Set both `workspace_access` and `shell_execute` to `false` explicitly in the manifest.

### "Tag version does not match manifest.json version"

Run `python scripts/update_version.py <tag-version-without-v>` locally, commit, then re-tag.

### "manifest.json missing from root" (verify_package)

You built the ZIP incorrectly. Always use `python scripts/build_package.py` — it places the manifest at the archive root and flattens `src/`.

### "SHA-256 mismatch"

The build is not reproducible. Ensure you are using `build_package.py` (deterministic timestamps) and that no `__pycache__` or junk files leaked into the archive.

### "Install fails at venv creation"

Confirm PELDRUN's backend Python is 3.12 (matching `manifest.runtime.python`). Also confirm your `requirements.txt` pins align with PELDRUN's backend pins.

### "pip resolver conflict at install time"

Your dependency pins conflict with PELDRUN's transitive requirements. Align `requirements.txt`, `manifest.json["dependencies"]`, and `pyproject.toml["dependencies"]` with the backend pins.

### Bootstrap reports "Unresolved placeholders remain"

A token survived the run. Check the reported file and token. This usually means a typo in a placeholder name. Fix it and re-run the bootstrap (it is idempotent).

### GitHub Actions expressions were replaced

This should not happen. The placeholder pattern only matches `{{WORD}}` without spaces or dots. Expressions like `${{ github.repository }}` contain spaces and are preserved. If you see corruption, check for a custom token that accidentally matches the pattern.

---

## 18. FAQ

**Q: Do I need to edit the automation scripts?**
A: No. All six scripts are generic and read provider-specific data from `manifest.json`. The only script you run once is `bootstrap_provider.py`.

**Q: Do I need to manually edit `release.yml` or `pyproject.toml` for brand color, icon, or author?**
A: No. The bootstrap script's legacy literal normalization automatically converts `"#000000"`, `default`, and `"Your Name"` into placeholders and fills them with your CLI values.

**Q: Will the bootstrap script ship inside the provider ZIP?**
A: No. `build_package.py` only includes `manifest.json`, `requirements.txt`, and the flattened `src/` package. The bootstrap script is also added to `.gitignore`.

**Q: Can I re-run the bootstrap script?**
A: Yes. It is idempotent. Files without placeholders are left untouched.

**Q: What Python version do I need?**
A: Python 3.12.x. The manifest declares `>=3.12,<3.13`, and other versions are rejected at install time.

**Q: Are the scripts dependent on third-party packages?**
A: No. All automation scripts are stdlib-only. They run in a bare CI environment.

**Q: What is the difference between the ZIP and `catalog-entry.json`?**
A: The ZIP is the installable provider package. `catalog-entry.json` is Store metadata (brand color, icon, download URL, checksum) and is **not** part of the ZIP.

**Q: How do I preview changes before applying them?**
A: Use `--dry-run` with the bootstrap script.

**Q: Why does the package directory get flattened?**
A: PELDRUN's installer resolves the `entry_point` from the archive root. The package must live at `<id_snake>_peldrun/`, not `src/<id_snake>_peldrun/`.

**Q: Can I use a dotted ID like `acme.ai`?**
A: Yes. The snake_case variant converts dots to underscores: `acme.ai` → `acme_ai` → package `acme_ai_peldrun`.

---

## 19. License

MIT — see [LICENSE](LICENSE).

---

## References

- [PELDRUN Provider Package Repository — Complete Developer Guide](https://github.com/peldrun/peldrun/blob/main/docs/providers/Provider%20Package%20Repository.md)
- [Reference implementation: peldrun-provider-cloudflare-ai](https://github.com/peldrunai/peldrun-provider-cloudflare-ai)
