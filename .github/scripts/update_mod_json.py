#!/usr/bin/env python3
"""Add a GitHub release to ModURL/mod.json so the OpenGOAL launcher sees it.

Run by .github/workflows/update-mod-json.yml. Needs the `gh` CLI, GH_TOKEN and
GH_REPO in the environment, plus TAG (the release tag, e.g. v0.0.12).
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

MOD_KEY = "BlastBot"            # key of your mod inside "mods" in mod.json
MOD_JSON = "ModURL/mod.json"    # path of the file in the repo

tag = os.environ["TAG"]
release = json.loads(
    subprocess.check_output(
        ["gh", "release", "view", tag, "--json", "tagName,publishedAt,assets"],
        text=True,
    )
)


def pick(predicate):
    for asset in release["assets"]:
        if predicate(asset["name"]):
            return asset
    return None


windows = pick(lambda n: n.startswith("windows-") and n.endswith(".zip"))
linux = pick(lambda n: n.startswith("linux-") and n.endswith(".tar.gz"))
macos = pick(lambda n: n.startswith("macos-intel-") and n.endswith(".tar.gz")) or pick(
    lambda n: n.startswith("macos-") and n.endswith(".tar.gz")
)

if windows is None:
    sys.exit(f"No windows-*.zip asset found on release {tag}; not touching mod.json")

with open(MOD_JSON, encoding="utf-8") as f:
    data = json.load(f)

mod = data["mods"][MOD_KEY]
versions = mod["versions"]
version = tag[1:] if tag.startswith("v") else tag


def url(asset):
    return asset["url"] if asset else None


def downloads(asset):
    return asset["downloadCount"] if asset else 0


entry = {
    "version": version,
    "publishedDate": release["publishedAt"],
    "supportedGames": mod["supportedGames"],
    # keep whatever settings the newest existing version uses
    "settings": versions[0]["settings"]
    if versions
    else {"decompConfigOverride": "", "shareVanillaSaves": False},
    "assets": {
        "windows": url(windows),
        "linux": url(linux),
        "macos": url(macos),
    },
    "assetDownloadCounts": {
        "windows": downloads(windows),
        "linux": downloads(linux),
        "macos": downloads(macos),
    },
}

# replace an existing entry for the same version, otherwise add as newest
mod["versions"] = [entry] + [v for v in versions if v["version"] != version]
data["lastUpdated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

with open(MOD_JSON, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"mod.json now lists {version} (newest first: {[v['version'] for v in mod['versions']]})")
