"""Portable Asteroid Erosion release builder and verification gates.

Python 3.11+, standard library only. Run from the repository root:
  python tools/release.py build --tag v0.2.0 --output release-dist
  python tools/release.py verify --tag v0.2.0 --output release-dist
The ZIP includes only PUBLIC_FILES; release tools, notes and tests stay outside it.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
import zipfile

REPOSITORY = "V0nCleef/EveJS-Asteroid-Erosion"
PUBLIC_FILES = (
    "loader.js", "config.json", "evejs-launcher.mod.json", "README.md", "VERIFICATION.md",
    "lib/radius.js", "lib/source.js", "lib/runtime.js", "lib/delivery.js",
    "client/preferences.py", "client/ui.py", "client/companion.py", "client/menu.py",
)
UPDATES = dict(provider="github", repository=REPOSITORY, asset="AsteroidErosion-{version}.zip",
               channel="stable", tagPrefix="v", preserveFiles=["config.json"])


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate manifest JSON field.")
            result[key] = value
        return result
    def nonfinite(_value):
        raise ValueError("Non-finite JSON values are unsupported.")
    return json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)


def regular_file(source, relative):
    path = source / relative
    if (not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(source)
            or any(parent.is_symlink() for parent in path.parents if parent != source and parent.is_relative_to(source))):
        raise ValueError(f"Missing or non-ordinary release file: {relative}")
    return path


def load_source(source, tag):
    source = Path(source).resolve(strict=True)
    manifest = strict_json(regular_file(source, "evejs-launcher.mod.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("The public mod manifest must be a JSON object.")
    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", version):
        raise ValueError("A stable three-component semantic version is required.")
    if tag != "v" + version:
        raise ValueError("Release tag must equal v plus the manifest version.")
    required = dict(schemaVersion=3, id="asteroid-erosion", kind="loader",
                    supportedBackends=["native"], activation=dict(strategy="loader_rename"),
                    restart="game_server", compatibility=dict(evejsVersions=["0.12.9"]),
                    launcherApi=dict(version=1, minLauncherVersion="1.0.69"),
                    clientMenu=dict(apiVersion=1, entrypoint="client/menu.py"), updates=UPDATES)
    allowed = set(required) | {"version", "displayName", "description", "settings",
                               "requires", "loadBefore", "loadAfter", "conflicts"}
    if set(manifest) - allowed:
        raise ValueError("Unsupported manifest fields; review the Launcher contract before releasing.")
    for key, expected in required.items():
        if manifest.get(key) != expected:
            raise ValueError(f"Release contract changed: {key}. Review the builder and migration before releasing.")
    if type(manifest["launcherApi"]["version"]) is not int or type(manifest["clientMenu"]["apiVersion"]) is not int:
        raise ValueError("Launcher and menu API versions must be integers.")
    notes = regular_file(source, f"releases/{version}.md")
    if not 0 < notes.stat().st_size <= 128 * 1024 or not notes.read_text(encoding="utf-8").strip():
        raise ValueError("Nonempty version-specific release notes are required (maximum 128 KiB).")
    files = {name: regular_file(source, name).read_bytes() for name in PUBLIC_FILES}
    if any(len(data) > 8 * 1024 * 1024 for data in files.values()) or sum(map(len, files.values())) > 16 * 1024 * 1024:
        raise ValueError("The explicit source package exceeds its release size limit.")
    if len(files["client/menu.py"]) > 128 * 1024:
        raise ValueError("The shared MODS menu entrypoint exceeds its API limit.")
    return source, manifest, files


def expected_assets(source, tag):
    source, manifest, files = load_source(source, tag)
    version = manifest["version"]
    name = UPDATES["asset"].replace("{version}", version)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for relative, data in files.items():
            info = zipfile.ZipInfo(relative, date_time=(2000, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    # Same schema and field order as the Launcher's public metadata authoring helper.
    metadata = dict(schemaVersion=1, id=manifest["id"], version=version, asset=name,
                    evejsVersions=manifest["compatibility"]["evejsVersions"])
    sidecar = (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    sidecar_name = name[:-4] + ".update.json"
    assets = {name: buffer.getvalue(), sidecar_name: sidecar}
    assets[f"AsteroidErosion-{version}-SHA256SUMS.txt"] = "".join(
        sha256(data) + "  " + filename + "\n" for filename, data in assets.items()).encode("ascii")
    return assets


def build(source, output, tag):
    assets = expected_assets(source, tag)  # All source/notes contracts pass before any output write.
    output = Path(output)
    for name, data in assets.items():
        target = output / name
        if target.exists() and (target.is_symlink() or target.read_bytes() != data):
            raise FileExistsError(f"Refusing to replace different release bytes: {target}")
    output.mkdir(parents=True, exist_ok=True)
    for name, data in assets.items():
        target = output / name
        if not target.exists():
            with target.open("xb") as stream:
                stream.write(data)
    verify(source, output, tag)
    return assets


def verify(source, output, tag):
    assets = expected_assets(source, tag)
    output = Path(output).resolve(strict=True)
    actual_names = {item.name for item in output.iterdir()}
    if actual_names != set(assets):
        raise ValueError("Release assets are missing, unexpected, or duplicated.")
    for name, data in assets.items():
        actual = regular_file(output, name).read_bytes()
        if actual != data:
            raise ValueError(f"Release asset differs from the checked source: {name}")
    archive_name = next(name for name in assets if name.endswith(".zip"))
    with zipfile.ZipFile(io.BytesIO(assets[archive_name])) as archive:
        if archive.testzip() is not None or archive.namelist() != list(PUBLIC_FILES):
            raise ValueError("Release ZIP differs from the explicit public file whitelist.")
    return assets


def api_request(repository, tag):
    if repository != REPOSITORY or not re.fullmatch(r"v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", tag):
        raise ValueError("Remote release repository or tag differs from the declared stable source.")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("A GitHub token is required for the draft release verification gate.")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/releases/tags/{tag}",
        headers={"Accept": "application/vnd.github+json", "Authorization": "Bearer " + token,
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "AsteroidErosion-Release/1"})
    return request


def ensure_absent(repository, tag):
    request = api_request(repository, tag)
    try:
        with urllib.request.urlopen(request, timeout=30):
            pass
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return
        raise ValueError(f"Cannot establish release absence: HTTP {error.code}") from None
    raise FileExistsError("This tag already has a GitHub release. Nothing was replaced.")


def verify_remote(source, output, repository, tag):
    assets = verify(source, output, tag)
    request = api_request(repository, tag)
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("GitHub returned an oversized release record.")
    release = json.loads(raw)
    if release.get("tag_name") != tag or release.get("draft") is not True or release.get("prerelease") is not False:
        raise ValueError("Uploaded assets must belong to the expected unpublished stable draft.")
    uploaded = release.get("assets", [])
    if not isinstance(uploaded, list) or len(uploaded) != len(assets) or {item.get("name") for item in uploaded} != set(assets):
        raise ValueError("Draft release assets are missing, unexpected, or duplicated.")
    for asset in uploaded:
        data = assets[asset["name"]]
        if (asset.get("state") != "uploaded" or asset.get("size") != len(data)
                or asset.get("digest") != "sha256:" + sha256(data)):
            raise ValueError("Draft release asset failed its name, size or digest verification.")
    return assets


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify", "ensure-absent", "verify-remote"))
    parser.add_argument("--source", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("release-dist"))
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repository", default=REPOSITORY)
    args = parser.parse_args()
    if args.command == "ensure-absent":
        # Source/tag/notes contracts also gate the first remote mutation.
        load_source(args.source, args.tag)
        ensure_absent(args.repository, args.tag)
        print("No existing release; preflight passed.")
    else:
        if args.command == "build":
            assets = build(args.source, args.output, args.tag)
        elif args.command == "verify":
            assets = verify(args.source, args.output, args.tag)
        else:
            assets = verify_remote(args.source, args.output, args.repository, args.tag)
        print(json.dumps({name: {"sha256": sha256(data), "bytes": len(data)}
                          for name, data in assets.items()}, indent=2))
