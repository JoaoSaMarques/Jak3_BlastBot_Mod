#!/usr/bin/env python3
"""Add GitHub releases to ModURL/mod.json so the OpenGOAL launcher sees them.

Run by .github/workflows/update-mod-json.yml. Needs the `gh` CLI, GH_TOKEN and
GH_REPO in the environment, plus TAG: a release tag (e.g. v0.0.12) or the word
"all" to add every published release in one go.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

MOD_KEY = "BlastBot"            # key of your mod inside "mods" in mod.json
MOD_JSON = "ModURL/mod.json"    # path of the file in the repo


def gh_json(*args):
    return json.loads(subprocess.check_output(["gh", *args], text=True))


requested = os.environ["TAG"]
if requested == "all":
    tags = [
        r["tagName"]
        for r in gh_json("release", "list", "--exclude-drafts", "--limit", "200", "--json", "tagName")
    ]
else:
    tags = [requested]

with open(MOD_JSON, encoding="utf-8") as f:
    data = json.load(f)

mod = data["mods"][MOD_KEY]
default_settings = (
    mod["versions"][0]["settings"]
    if mod["versions"]
    else {"decompConfigOverride": "", "shareVanillaSaves": False}
)
added = []

for tag in tags:
    release = gh_json("release", "view", tag, "--json", "tagName,publishedAt,assets")

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
        message = f"No windows-*.zip asset found on release {tag}"
        if requested == "all":
            print(f"Skipping {tag}: {message}")
            continue
        sys.exit(f"{message}; not touching mod.json")

    def url(asset):
        return asset["url"] if asset else None

    def downloads(asset):
        return asset["downloadCount"] if asset else 0

    version = tag[1:] if tag.startswith("v") else tag
    entry = {
        "version": version,
        "publishedDate": release["publishedAt"],
        "supportedGames": mod["supportedGames"],
        "settings": default_settings,
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
    # replace an existing entry for the same version, otherwise add it
    mod["versions"] = [entry] + [v for v in mod["versions"] if v["version"] != version]
    added.append(version)

# newest first, whatever order the releases were added in
mod["versions"].sort(key=lambda v: v["publishedDate"], reverse=True)
data["lastUpdated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

with open(MOD_JSON, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"Added/updated: {added}")
print(f"mod.json now lists (newest first): {[v['version'] for v in mod['versions']]}")
