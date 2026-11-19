#!/usr/bin/env python3
"""
One-time template initializer for a PELDRUN provider repository.

Replaces every {{PLACEHOLDER}} token across the repository with concrete
provider values, renames placeholder directories (e.g. the src/ package),
and validates the provider ID against PELDRUN's manifest rules.

The script is stdlib-only, preserves line endings, JSON-escapes values
written into .json files, skips binary files, and never rewrites itself.
It is safe to re-run: files without placeholders are left untouched.

Usage:
    python scripts/bootstrap_provider.py --id my-provider
    python scripts/bootstrap_provider.py --id my-provider \
        --display-name "My Provider AI" \
        --author "Your Name" \
        --brand-color "#F38020" \
        --icon myprovider

    # Preview every change without writing anything:
    python scripts/bootstrap_provider.py --id my-provider --dry-run

Exit codes:
    0 - success
    1 - invalid arguments, or unresolved placeholders remain after the run
    2 - filesystem error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent
SELF_PATH = Path(__file__).resolve()

# Directories that must never be scanned or modified.
SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn", "dist", "build", "__pycache__",
    ".venv", "venv", "env", ".tox", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules", ".idea", ".vscode",
})

# Provider ID rule - mirrors scripts/validate_manifest.py.
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

# IDs reserved by PELDRUN's built-in adapters.
BUILTIN_IDS = frozenset({
    "openai_compat", "lmstudio", "ollama", "openai_native",
    "anthropic", "google_genai", "ollama_native", "lmstudio_native",
})

# Any {{TOKEN}} that survives the run is reported as unresolved.
PLACEHOLDER_RE = re.compile(r"\{\{[A-Za-z_][A-Za-z0-9_]*\}\}")

# Words rendered as acronyms when auto-deriving the display name.
ACRONYMS = {"ai": "AI", "api": "API", "llm": "LLM", "gpt": "GPT", "ml": "ML"}

# Files larger than this are assumed to be assets and are skipped.
MAX_FILE_BYTES = 2 * 1024 * 1024

HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# ---------------------------------------------------------------------------
# Legacy literal normalization
# ---------------------------------------------------------------------------
# Some template revisions ship concrete default values instead of placeholders
# in a few tooling files. This map upgrades those literals to canonical tokens
# before the main replacement pass runs.
#
# Each entry is scoped to one file and contains:
#   (relative_file_path, regex_pattern, regex_replacement)
#
# The patterns are intentionally conservative: they only match untouched
# template defaults, never user-customized values.

LEGACY_LITERAL_PATCHES: tuple[tuple[str, str, str], ...] = (
    (
        ".github/workflows/release.yml",
        r'(--brand-color\s+)"#000000"',
        r'\1"{{BRAND_COLOR}}"',
    ),
    (
        ".github/workflows/release.yml",
        r"(--icon\s+)default(?=\s|$)",
        r"\1{{ICON_NAME}}",
    ),
    (
        "pyproject.toml",
        r'(authors\s*=\s*\[\s*\{\s*name\s*=\s*)"Your Name"',
        r'\1"{{AUTHOR_NAME}}"',
    ),
)


def normalize_legacy_literals(dry_run: bool) -> list[str]:
    """
    Upgrade known hardcoded template defaults to placeholder tokens.

    This allows the bootstrap script to fully initialize repositories created
    from older template versions without requiring manual edits to release.yml
    or pyproject.toml.

    Returns a list of human-readable change descriptions.
    """
    changes: list[str] = []

    for rel_path, pattern, replacement in LEGACY_LITERAL_PATCHES:
        path = REPO_ROOT / rel_path
        if not path.is_file():
            continue

        text = read_text(path)
        if text is None:
            continue

        updated, count = re.subn(pattern, replacement, text)
        if count == 0:
            continue

        if not dry_run:
            try:
                path.write_bytes(updated.encode("utf-8"))
            except OSError as exc:
                print(f"[err] Could not normalize {rel_path}: {exc}", file=sys.stderr)
                continue

        changes.append(
            f"{rel_path} ({count} legacy literal{'s' if count != 1 else ''} normalized)"
        )

    return changes


def derive_names(provider_id: str, display_name: str | None) -> dict[str, str]:
    """Derive every naming variant from the canonical provider ID."""
    snake = provider_id.replace("-", "_").replace(".", "_")
    class_name = "".join(part.capitalize() for part in snake.split("_") if part)
    if not display_name:
        words = [w for w in re.split(r"[-_.]+", provider_id) if w]
        display_name = " ".join(ACRONYMS.get(w, w.capitalize()) for w in words)
    return {
        "id": provider_id,
        "snake": snake,
        "class_name": class_name,
        "display": display_name,
    }


def build_replacements(args: argparse.Namespace, names: dict[str, str]) -> dict[str, str]:
    """Map every template token to its concrete value."""
    return {
        "{{PROVIDER_ID}}": names["id"],
        "{{PROVIDER_ID_SNAKE}}": names["snake"],
        "{{PROVIDER_DISPLAY_NAME}}": names["display"],
        "{{PROVIDER_NAME}}": names["display"],
        "{{ProviderClassName}}": names["class_name"],
        "{{AUTHOR_NAME}}": args.author,
        "{{AUTHOR_URL}}": args.author_url,
        "{{HOMEPAGE_URL}}": args.homepage_url,
        "{{ICON_NAME}}": args.icon or names["snake"],
        "{{BRAND_COLOR}}": args.brand_color,
        # Stub package path shipped in the template's update_version.py.
        "CHANGE_ME_peldrun": f"{names['snake']}_peldrun",
    }


def iter_text_files() -> Iterator[Path]:
    """Yield every candidate file, pruning ignored directories."""
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if path.resolve() == SELF_PATH:
                # Never rewrite this script's own replacement map.
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield path


def read_text(path: Path) -> str | None:
    """Return file content as UTF-8 text, or None for binary/unreadable files."""
    try:
        return path.read_bytes().decode("utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def apply_replacements(text: str, replacements: dict[str, str]) -> tuple[str, int]:
    """Replace tokens longest-first; return the new text and the hit count."""
    total = 0
    for token in sorted(replacements, key=len, reverse=True):
        hits = text.count(token)
        if hits:
            text = text.replace(token, replacements[token])
            total += hits
    return text, total


def rename_placeholder_dirs(replacements: dict[str, str], dry_run: bool) -> list[str]:
    """Rename directories whose names contain tokens, deepest first."""
    targets: list[Path] = []
    for dirpath, dirnames, _ in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        targets.extend(Path(dirpath) / d for d in dirnames if PLACEHOLDER_RE.search(d))

    renamed: list[str] = []
    for path in sorted(targets, key=lambda p: len(p.parts), reverse=True):
        new_name, _ = apply_replacements(path.name, replacements)
        if new_name == path.name:
            continue
        dest = path.with_name(new_name)
        if dest.exists():
            print(f"[warn] Skip rename {path.name!r}: target {new_name!r} already exists.",
                  file=sys.stderr)
            continue
        if not dry_run:
            try:
                path.rename(dest)
            except OSError as exc:
                print(f"[err] Could not rename {path}: {exc}", file=sys.stderr)
                continue
        renamed.append(
            f"{path.relative_to(REPO_ROOT).as_posix()} -> {dest.relative_to(REPO_ROOT).as_posix()}"
        )
    return renamed


def ensure_gitignore_entry() -> bool:
    """Exclude this one-time initializer from version control."""
    rel = SELF_PATH.relative_to(REPO_ROOT).as_posix()
    path = REPO_ROOT / ".gitignore"
    existing = read_text(path) if path.is_file() else ""
    if existing is None:
        return False
    if any(line.strip() == rel for line in existing.splitlines()):
        return False
    block = (
        "\n# One-time template initializer; local tooling only, never shipped.\n"
        f"{rel}\n"
    )
    new_text = (existing.rstrip("\n") + "\n" + block) if existing else block.lstrip("\n")
    try:
        path.write_bytes(new_text.encode("utf-8"))
    except OSError:
        return False
    return True


def scan_leftovers() -> dict[str, list[str]]:
    """Report any {{TOKEN}} still present in text files after the run."""
    leftovers: dict[str, list[str]] = {}
    for path in iter_text_files():
        text = read_text(path)
        if text is None:
            continue
        tokens = sorted(set(PLACEHOLDER_RE.findall(text)))
        if tokens:
            leftovers[path.relative_to(REPO_ROOT).as_posix()] = tokens
    return leftovers


def print_next_steps(names: dict[str, str]) -> None:
    print()
    print("Next steps:")
    print(f"  1. Optionally rename the repository root folder to 'peldrun-provider-{names['id']}'.")
    print(f"  2. Fill in manifest.json and src/{names['snake']}_peldrun/adapter.py.")
    print("  3. python scripts/validate_manifest.py")
    print("  4. python scripts/build_package.py && python scripts/verify_package.py")


def run(args: argparse.Namespace) -> int:
    provider_id = args.id.strip().lower()
    if not ID_RE.match(provider_id):
        print(f"[err] Invalid provider ID {args.id!r}. Must match {ID_RE.pattern}",
              file=sys.stderr)
        return 1
    if provider_id in BUILTIN_IDS:
        print(f"[err] Provider ID {provider_id!r} collides with a built-in adapter.",
              file=sys.stderr)
        return 1
    if not HEX_COLOR_RE.match(args.brand_color):
        print(f"[err] --brand-color must be a hex color like '#F38020', got {args.brand_color!r}",
              file=sys.stderr)
        return 1
    if args.icon and not ID_RE.match(args.icon):
        print(f"[err] --icon must be a lowercase slug, got {args.icon!r}", file=sys.stderr)
        return 1
    for label, value in (("--display-name", args.display_name), ("--author", args.author),
                         ("--author-url", args.author_url), ("--homepage-url", args.homepage_url)):
        if value and ("\n" in value or "\r" in value):
            print(f"[err] {label} must not contain line breaks.", file=sys.stderr)
            return 1

    names = derive_names(provider_id, args.display_name)
    replacements = build_replacements(args, names)
    # Values embedded in JSON strings must be escaped to keep the file valid.
    json_replacements = {
        token: json.dumps(value, ensure_ascii=False)[1:-1]
        for token, value in replacements.items()
    }

    print("PELDRUN provider bootstrap")
    print(f"  id:           {names['id']}")
    print(f"  package:      {names['snake']}_peldrun")
    print(f"  adapter:      {names['class_name']}Adapter")
    print(f"  display name: {names['display']}")
    print(f"  mode:         {'dry-run (no writes)' if args.dry_run else 'write'}")
    print()

    # Normalize old hardcoded template defaults before replacing placeholders.
    # This makes --brand-color, --icon, and --author work even when the template
    # still contains literal values such as "#000000", "default", or "Your Name".
    normalized = normalize_legacy_literals(args.dry_run)
    for line in normalized:
        tag = "dry" if args.dry_run else "ok "
        print(f"  [{tag}] normalized {line}")

    changed = 0
    total_hits = 0
    for path in iter_text_files():
        text = read_text(path)
        if text is None:
            continue
        mapping = json_replacements if path.suffix == ".json" else replacements
        updated, hits = apply_replacements(text, mapping)
        if not hits:
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if not args.dry_run:
            try:
                path.write_bytes(updated.encode("utf-8"))
            except OSError as exc:
                print(f"[err] Could not write {rel}: {exc}", file=sys.stderr)
                return 2
        changed += 1
        total_hits += hits
        tag = "dry" if args.dry_run else "ok "
        print(f"  [{tag}] {rel} ({hits} replacement{'s' if hits != 1 else ''})")

    renamed = rename_placeholder_dirs(replacements, args.dry_run)
    for line in renamed:
        tag = "dry" if args.dry_run else "ok "
        print(f"  [{tag}] renamed {line}")

    if not args.dry_run and ensure_gitignore_entry():
        print("  [ok ] .gitignore (bootstrap script excluded from version control)")

    print()
    print(f"Done: {changed} file(s) updated, {total_hits} replacement(s), "
          f"{len(renamed)} directory rename(s).")

    if not args.dry_run:
        leftovers = scan_leftovers()
        if leftovers:
            print()
            print("[warn] Unresolved placeholders remain:", file=sys.stderr)
            for rel, tokens in leftovers.items():
                print(f"  {rel}: {', '.join(tokens)}", file=sys.stderr)
            return 1
        print_next_steps(names)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Initialize a PELDRUN provider repository from the template.",
    )
    parser.add_argument("--id", required=True,
                        help="Provider ID (lowercase, e.g. 'my-provider').")
    parser.add_argument("--display-name", default=None,
                        help="Human-friendly name. Derived from --id when omitted.")
    parser.add_argument("--author", default="PELDRUN Community",
                        help="Author name for the manifest and pyproject.")
    parser.add_argument("--author-url", default="", help="Author profile URL.")
    parser.add_argument("--homepage-url", default="", help="Provider homepage URL.")
    parser.add_argument("--icon", default=None,
                        help="Store icon slug. Defaults to the snake_case ID.")
    parser.add_argument("--brand-color", default="#000000",
                        help="Hex brand color, e.g. '#F38020'.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing anything.")
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())