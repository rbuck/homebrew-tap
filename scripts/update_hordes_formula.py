#!/usr/bin/env python3
"""Update Formula/hordes.rb from a published hordes-rs release."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


REPOSITORY = "rbuck/hordes-rs"
PLATFORMS = {
    "aarch64-apple-darwin": "  if OS.mac? && Hardware::CPU.arm?",
    "x86_64-apple-darwin": "  if OS.mac? && Hardware::CPU.intel?",
    "x86_64-unknown-linux-gnu": "  if OS.linux? && Hardware::CPU.intel?",
}


def run(command, *, env=None):
    return subprocess.run(
        command, check=True, capture_output=True, text=True, env=env
    ).stdout


def release_assets(tag):
    try:
        output = run(
            [
                "gh",
                "api",
                f"repos/{REPOSITORY}/releases/tags/{tag}",
                "--jq",
                ".assets[] | {id: .id, name: .name, api_url: .url}",
            ]
        )
    except subprocess.CalledProcessError as error:
        if "404" in error.stderr or "Not Found" in error.stderr:
            raise ValueError(
                f"release {tag} was not found; publish that GitHub release first"
            ) from error
        raise
    return {asset["name"]: asset for asset in map(json.loads, output.splitlines())}


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
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", line)
        if match:
            checksums[match.group(2).strip()] = match.group(1).lower()
    return checksums


def update_block(formula, condition, url, checksum):
    pattern = re.compile(
        rf"(?P<block>^  if {re.escape(condition.removeprefix('  if '))}\n.*?^  end)",
        re.MULTILINE | re.DOTALL,
    )
    matches = list(pattern.finditer(formula))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one formula block for {condition}")

    block = matches[0].group("block")
    block, url_count = re.subn(
        r'(?m)^(\s*url )"[^"]+"',
        lambda match: f'{match.group(1)}"{url}"',
        block,
        count=1,
    )
    block, checksum_count = re.subn(
        r'(?m)^(\s*sha256 )"[0-9a-fA-F]{64}"',
        lambda match: f'{match.group(1)}"{checksum}"',
        block,
        count=1,
    )
    if url_count != 1 or checksum_count != 1:
        raise ValueError(f"could not locate URL and SHA256 in {condition}")
    return formula[: matches[0].start()] + block + formula[matches[0].end() :]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="release tag, for example v0.7.3")
    parser.add_argument(
        "--formula",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "Formula/hordes.rb",
        help="formula file to update (defaults to this repository's Formula/hordes.rb)",
    )
    args = parser.parse_args()

    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", args.tag):
        parser.error("tag must look like v0.7.3")

    env = os.environ.copy()
    env["HOMEBREW_GITHUB_API_TOKEN"] = run(["gh", "auth", "token"]).strip()
    if not env["HOMEBREW_GITHUB_API_TOKEN"]:
        parser.error("gh auth token returned an empty token")

    assets = release_assets(args.tag)
    version = args.tag.removeprefix("v")
    asset_names = {
        target: f"hordes-{version}-{target}.tar.gz" for target in PLATFORMS
    }
    checksum_asset = assets.get("SHA256SUMS.txt")
    if checksum_asset is None:
        parser.error("release is missing SHA256SUMS.txt")

    checksums = release_checksums(checksum_asset, env)
    missing = [name for name in asset_names.values() if name not in assets]
    missing.extend(name for name in asset_names.values() if name not in checksums)
    if missing:
        parser.error("release is missing required assets/checksums: " + ", ".join(missing))

    formula = args.formula.read_text()
    updated = formula
    for target, condition in PLATFORMS.items():
        asset_name = asset_names[target]
        asset = assets[asset_name]
        url = (
            asset["api_url"]
            if target.endswith("apple-darwin")
            else f"https://github.com/{REPOSITORY}/releases/download/{args.tag}/{asset_name}"
        )
        updated = update_block(updated, condition, url, checksums[asset_name])

    args.formula.write_text(updated)
    print(f"Updated {args.formula} for {args.tag}")


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
