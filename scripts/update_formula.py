#!/usr/bin/env python3
"""Update a Homebrew formula from a GitHub release and its SHA256SUMS.txt."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


def run(command, *, env=None):
    return subprocess.run(
        command, check=True, capture_output=True, text=True, env=env
    ).stdout


def github_repository(formula):
    match = re.search(
        r'(?m)^\s*homepage\s+"https?://github\.com/([^/]+)/([^/"#]+)',
        formula,
    )
    if not match:
        raise ValueError("formula homepage must identify a GitHub repository")
    return f"{match.group(1)}/{match.group(2).removesuffix('.git')}"


def formula_blocks(formula):
    blocks = re.finditer(
        r"(?ms)^  if (?P<condition>[^\n]+)\n(?P<body>.*?)(?=^  end\s*$)",
        formula,
    )
    result = []
    for match in blocks:
        body = match.group("body")
        url = re.search(r'(?m)^\s*url\s+"([^"]+)"', body)
        checksum = re.search(r'(?m)^\s*sha256\s+"([0-9a-fA-F]{64})"', body)
        if url and checksum:
            result.append(
                (match.start(), match.end(), match.group("condition"), url, checksum)
            )
    if not result:
        raise ValueError("formula has no platform blocks with both url and sha256")
    return result


def release_assets(repository, tag):
    try:
        output = run(
            [
                "gh",
                "api",
                f"repos/{repository}/releases/tags/{tag}",
                "--jq",
                ".assets[] | {id: .id, name: .name, api_url: .url}",
            ]
        )
    except subprocess.CalledProcessError as error:
        if "404" in error.stderr or "Not Found" in error.stderr:
            raise ValueError(
                f"release {tag} was not found in {repository}"
            ) from error
        raise
    return {asset["name"]: asset for asset in map(json.loads, output.splitlines())}


def current_asset_name(repository, url):
    match = re.search(r"/releases/assets/(\d+)(?:[?#].*)?$", url)
    if match:
        return run(
            [
                "gh",
                "api",
                f"repos/{repository}/releases/assets/{match.group(1)}",
                "--jq",
                ".name",
            ]
        ).strip()
    return unquote(Path(urlparse(url).path).name)


def expected_asset_name(current_name, tag):
    version = tag.removeprefix("v")
    semver = re.compile(r"(?<![A-Za-z0-9])(?P<prefix>v?)\d+\.\d+\.\d+")
    if semver.search(current_name):
        return semver.sub(lambda match: f"{match.group('prefix')}{version}", current_name)
    return current_name


def checksum_asset(assets):
    for name in assets:
        if name.lower() == "sha256sums.txt":
            return assets[name]
    raise ValueError("release is missing SHA256SUMS.txt")


def release_checksums(asset, env):
    output = run(
        [
            "curl",
            "-f",
            "-L",
            "-sS",
            "-H",
            "Accept: application/octet-stream",
            "-H",
            f"Authorization: Bearer {env['HOMEBREW_GITHUB_API_TOKEN']}",
            "-H",
            "X-GitHub-Api-Version: 2022-11-28",
            asset["api_url"],
        ],
        env=env,
    )
    checksums = {}
    for line in output.splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", line.strip())
        if match:
            checksums[Path(match.group(2).strip()).name] = match.group(1).lower()
    return checksums


def updated_url(current_url, asset, tag, asset_name):
    if re.search(r"/releases/assets/\d+(?:[?#].*)?$", current_url):
        return asset["api_url"]
    parsed = urlparse(current_url)
    if parsed.hostname == "github.com" and "/releases/download/" in parsed.path:
        path = re.sub(
            r"/releases/download/[^/]+/[^/]+$",
            f"/releases/download/{tag}/{asset_name}",
            parsed.path,
        )
        return parsed._replace(path=path).geturl()
    return parsed._replace(
        path=str(Path(parsed.path).with_name(asset_name))
    ).geturl()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formula", help="formula filename without .rb, e.g. hordes")
    parser.add_argument("tag", help="GitHub release tag, e.g. v0.7.3")
    parser.add_argument(
        "--formula-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "Formula",
        help="directory containing formula files",
    )
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.formula):
        parser.error("formula must be a filename stem, e.g. hordes")
    if not re.fullmatch(r"v?\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", args.tag):
        parser.error("tag must look like v0.7.3")

    formula_path = args.formula_dir / f"{args.formula}.rb"
    formula = formula_path.read_text()
    repository = github_repository(formula)
    tag = args.tag if args.tag.startswith("v") else f"v{args.tag}"
    assets = release_assets(repository, tag)
    env = os.environ.copy()
    env["HOMEBREW_GITHUB_API_TOKEN"] = run(["gh", "auth", "token"]).strip()
    if not env["HOMEBREW_GITHUB_API_TOKEN"]:
        raise ValueError("gh auth token returned an empty token")
    checksums = release_checksums(checksum_asset(assets), env)
    if not checksums:
        raise ValueError("SHA256SUMS.txt contained no checksums")

    blocks = formula_blocks(formula)
    replacements = []
    for start, end, condition, url_match, checksum_match in blocks:
        old_url = url_match.group(1)
        old_name = current_asset_name(repository, old_url)
        asset_name = expected_asset_name(old_name, tag)
        asset = assets.get(asset_name)
        if asset is None:
            raise ValueError(
                f"release asset {asset_name!r} inferred from the {condition!r} "
                "formula block was not found"
            )
        sha256 = checksums.get(asset_name)
        if sha256 is None:
            raise ValueError(f"SHA256SUMS.txt has no checksum for {asset_name}")

        body = formula[start:end]
        body = body.replace(old_url, updated_url(old_url, asset, tag, asset_name), 1)
        body = body.replace(checksum_match.group(1), sha256, 1)
        replacements.append((start, end, body))

    updated = formula
    for start, end, body in reversed(replacements):
        updated = updated[:start] + body + updated[end:]
    formula_path.write_text(updated)
    print(f"Updated {formula_path} from {repository} release {tag}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or f"command failed: {error.cmd[0]}"
        print(f"error: {message}", file=sys.stderr)
        sys.exit(error.returncode or 1)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
