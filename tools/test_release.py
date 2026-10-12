"""Focused portable release gates. No network calls, dependencies or game files."""
from __future__ import annotations

from copy import deepcopy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import urllib.error
import zipfile

import release


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source, self.output = self.root / "source", self.root / "dist"
        self.source.mkdir()
        self.tag = "v0.2.0"
        self.manifest = dict(schemaVersion=3, id="asteroid-erosion", displayName="Asteroid Erosion",
                             version="0.2.0", kind="loader", supportedBackends=["native"],
                             activation=dict(strategy="loader_rename"), restart="game_server",
                             compatibility=dict(evejsVersions=["0.12.9"]),
                             launcherApi=dict(version=1, minLauncherVersion="1.0.69"),
                             clientMenu=dict(apiVersion=1, entrypoint="client/menu.py"),
                             updates=deepcopy(release.UPDATES))
        for filename in release.PUBLIC_FILES:
            path = self.source / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("Owned release fixture: " + filename + "\n").encode())
        self.write_manifest()
        notes = self.source / "releases/0.2.0.md"
        notes.parent.mkdir()
        notes.write_text("# Asteroid Erosion 0.2.0\n\nRelease fixture notes.\n", encoding="utf-8")

    def write_manifest(self):
        (self.source / "evejs-launcher.mod.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def assets(self):
        return release.build(self.source, self.output, self.tag)

    def draft(self, assets):
        return dict(id=410733053, tag_name=self.tag, draft=True, prerelease=False, target_commitish="a" * 40, assets=[
            dict(name=name, state="uploaded", size=len(data), digest="sha256:" + release.sha256(data))
            for name, data in assets.items()])

    def remote(self, data):
        entries = data if isinstance(data, list) else [data]
        return mock.patch.object(release.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(entries).encode()))

    def test_package_metadata_and_checksums_are_complete(self):
        assets = self.assets()
        self.assertEqual(set(assets), {"AsteroidErosion-0.2.0.zip", "AsteroidErosion-0.2.0.update.json",
                                      "AsteroidErosion-0.2.0-SHA256SUMS.txt"})
        with zipfile.ZipFile(io.BytesIO(assets["AsteroidErosion-0.2.0.zip"])) as archive:
            self.assertEqual(archive.namelist(), list(release.PUBLIC_FILES))
            self.assertIsNone(archive.testzip())
            for name in release.PUBLIC_FILES:
                self.assertEqual(archive.read(name), (self.source / name).read_bytes())
        self.assertEqual(json.loads(assets["AsteroidErosion-0.2.0.update.json"]),
                         dict(schemaVersion=1, id="asteroid-erosion", version="0.2.0",
                              asset="AsteroidErosion-0.2.0.zip", evejsVersions=["0.12.9"]))
        for line in assets["AsteroidErosion-0.2.0-SHA256SUMS.txt"].decode().splitlines():
            digest, name = line.split("  ")
            self.assertEqual(digest, release.sha256(assets[name]))
        self.assertEqual(release.verify(self.source, self.output, self.tag), assets)

    def test_missing_or_empty_version_notes_fail_before_output(self):
        notes = self.source / "releases/0.2.0.md"
        notes.unlink()
        for text in (None, "", " \n"):
            if text is not None:
                notes.write_text(text)
            with self.assertRaises(ValueError):
                self.assets()
            self.assertFalse(self.output.exists())

    def test_tag_and_stable_version_must_agree(self):
        for tag in ("0.2.0", "v0.2.1", "v0.2.0-rc.1", "v00.2.0"):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                release.build(self.source, self.output, tag)
        self.manifest["version"] = "0.2.0-rc.1"
        self.write_manifest()
        with self.assertRaises(ValueError):
            release.build(self.source, self.output, "v0.2.0-rc.1")
        self.assertFalse(self.output.exists())

    def test_ambiguous_or_nonfinite_manifest_json_is_rejected(self):
        path = self.source / "evejs-launcher.mod.json"
        valid = json.dumps(self.manifest)
        for text in ('{"version":"0.1.6",' + valid[1:], valid[:-1] + ',"settings":NaN}', '[]'):
            path.write_text(text)
            with self.assertRaises(ValueError):
                self.assets()
            self.assertFalse(self.output.exists())

    def test_update_preservation_menu_and_minimum_contracts_are_required(self):
        original = deepcopy(self.manifest)
        changes = [lambda m: m.pop("updates"), lambda m: m["updates"].update(preserveFiles=[]),
                   lambda m: m["updates"].update(repository="someone/else"),
                   lambda m: m["updates"].update(asset="Wrong-{version}.zip"),
                   lambda m: m["updates"].update(channel="prerelease"),
                   lambda m: m["updates"].update(tagPrefix="release-"),
                   lambda m: m.pop("clientMenu"), lambda m: m["clientMenu"].update(entrypoint="other.py"),
                   lambda m: m["clientMenu"].update(apiVersion=True),
                   lambda m: m["launcherApi"].update(minLauncherVersion="1.0.55"),
                   lambda m: m.update(unsupportedField="reject")]
        for index, change in enumerate(changes):
            with self.subTest(change=index):
                self.manifest = deepcopy(original)
                change(self.manifest)
                self.write_manifest()
                with self.assertRaises(ValueError):
                    self.assets()
                self.assertFalse(self.output.exists())

    def test_missing_public_file_and_oversized_menu_are_rejected(self):
        path = self.source / "client/menu.py"
        path.unlink()
        with self.assertRaises(ValueError):
            self.assets()
        path.write_bytes(b"x" * (128 * 1024 + 1))
        with self.assertRaises(ValueError):
            self.assets()
        self.assertFalse(self.output.exists())

    def test_explicit_whitelist_and_reproducible_immutable_zip(self):
        (self.source / "private-token.txt").write_text("Never package this fixture.")
        first = self.assets()
        for name in release.PUBLIC_FILES:
            os.utime(self.source / name, (1000000000, 1000000000))
        self.assertEqual(self.assets(), first)
        changed = self.source / "README.md"
        changed.write_text("Changed source with the same version.")
        before = {name: (self.output / name).read_bytes() for name in first}
        with self.assertRaises(FileExistsError):
            self.assets()
        self.assertEqual({name: (self.output / name).read_bytes() for name in first}, before)

    def test_verifier_rejects_missing_corrupt_or_extra_assets(self):
        assets = self.assets()
        sidecar = self.output / "AsteroidErosion-0.2.0.update.json"
        sidecar.unlink()
        with self.assertRaises(ValueError):
            release.verify(self.source, self.output, self.tag)
        sidecar.write_bytes(b"{}")
        with self.assertRaises(ValueError):
            release.verify(self.source, self.output, self.tag)
        sidecar.write_bytes(assets[sidecar.name])
        (self.output / "unexpected.zip").write_bytes(b"not reviewed")
        with self.assertRaises(ValueError):
            release.verify(self.source, self.output, self.tag)

    @mock.patch.dict(os.environ, {"GH_TOKEN": "fixture-token"})
    def test_duplicate_and_unavailable_remote_checks_fail_closed(self):
        existing = self.draft({})
        with self.remote(existing), self.assertRaises(FileExistsError):
            release.ensure_absent(release.REPOSITORY, self.tag)
        with self.remote([]):
            release.ensure_absent(release.REPOSITORY, self.tag)
        for code in (401, 403, 404, 500):
            error = urllib.error.HTTPError("https://api.github.com/fixture", code, "fixture", {}, None)
            with mock.patch.object(release.urllib.request, "urlopen", side_effect=error), self.assertRaises(ValueError):
                release.ensure_absent(release.REPOSITORY, self.tag)
        with self.assertRaises(ValueError):
            release.ensure_absent("someone/else", self.tag)
        # Exact tag only; similarly named tags do not block a new release.
        with self.remote(dict(existing, tag_name=self.tag + "-other")):
            release.ensure_absent(release.REPOSITORY, self.tag)
        # Duplicate exact tags, including a published/draft pair, are ambiguous.
        with self.remote([existing, dict(existing, id=123, draft=False)]), self.assertRaises(ValueError):
            release.ensure_absent(release.REPOSITORY, self.tag)
        other = dict(existing, id=1, tag_name="v0.1.6", draft=False)
        other2 = dict(other, id=2, tag_name="v0.1.5")
        def pages(*values):
            effects = [value if isinstance(value, Exception) else io.BytesIO(json.dumps(value).encode()) for value in values]
            return mock.patch.object(release.urllib.request, "urlopen", side_effect=effects)
        with mock.patch.object(release, "RELEASES_PER_PAGE", 2):
            with pages([other, other2], [existing]) as requests, self.assertRaises(FileExistsError):
                release.ensure_absent(release.REPOSITORY, self.tag)
            self.assertEqual([call.args[0].full_url.rsplit("page=", 1)[1] for call in requests.call_args_list], ["1", "2"])
            # Finding a match is not enough if a later page cannot be audited.
            with pages([existing, other], urllib.error.URLError("fixture unavailable")), self.assertRaises(ValueError):
                release.ensure_absent(release.REPOSITORY, self.tag)
            with pages([other, other2], [other]), self.assertRaises(ValueError):
                release.ensure_absent(release.REPOSITORY, self.tag)
            with mock.patch.object(release, "MAX_RELEASE_PAGES", 1), pages([other, other2]), self.assertRaises(ValueError):
                release.ensure_absent(release.REPOSITORY, self.tag)
            scan_limit = len(json.dumps([other, other2]).encode()) + 1
            with mock.patch.object(release, "MAX_RELEASE_SCAN_BYTES", scan_limit), pages([other, other2], [existing]), self.assertRaises(ValueError):
                release.ensure_absent(release.REPOSITORY, self.tag)
        malformed = [b"not JSON", b"{}", b"[{}]", b'[null]', b'[{"id":1,"id":2}]',
                     json.dumps([dict(existing, draft="true")]).encode()]
        for raw in malformed:
            with mock.patch.object(release.urllib.request, "urlopen", return_value=io.BytesIO(raw)), self.assertRaises(ValueError):
                release.ensure_absent(release.REPOSITORY, self.tag)
        with mock.patch.object(release, "MAX_RELEASE_PAGE_BYTES", 32), self.remote(existing), self.assertRaises(ValueError):
            release.ensure_absent(release.REPOSITORY, self.tag)

    @mock.patch.dict(os.environ, {"GH_TOKEN": "fixture-token"})
    def test_only_complete_matching_unpublished_draft_can_publish(self):
        assets = self.assets()
        draft = self.draft(assets)
        with self.remote(draft):
            self.assertEqual(release.verify_remote(self.source, self.output, release.REPOSITORY, self.tag), assets)
        # Reproduce GitHub's draft behavior: tag endpoint 404, authenticated list succeeds.
        requests = []
        def tag_404_but_list_draft(request, **_kwargs):
            requests.append(request.full_url)
            if "/releases/tags/" in request.full_url:
                raise urllib.error.HTTPError(request.full_url, 404, "draft hidden by tag endpoint", {}, None)
            self.assertIn("/releases?per_page=100&page=1", request.full_url)
            self.assertEqual(request.get_header("Authorization"), "Bearer fixture-token")
            return io.BytesIO(json.dumps([draft]).encode())
        with mock.patch.object(release.urllib.request, "urlopen", side_effect=tag_404_but_list_draft):
            self.assertEqual(release.verify_remote(self.source, self.output, release.REPOSITORY, self.tag, "a" * 40), assets)
            with self.assertRaises(FileExistsError):
                release.ensure_absent(release.REPOSITORY, self.tag)
        self.assertTrue(requests)
        self.assertFalse(any("/releases/tags/" in url for url in requests))
        for commit in ("b" * 40, "main", "not-a-sha"):
            with self.remote(draft), self.assertRaises(ValueError):
                release.verify_remote(self.source, self.output, release.REPOSITORY, self.tag, commit)
        # Draft selection works past the first page and still enforces exact assets.
        other = dict(draft, id=123, tag_name="v0.1.6", draft=False)
        other2 = dict(other, id=124, tag_name="v0.1.5")
        with mock.patch.object(release, "RELEASES_PER_PAGE", 2), mock.patch.object(release.urllib.request, "urlopen", side_effect=[
                io.BytesIO(json.dumps([other, other2]).encode()), io.BytesIO(json.dumps([draft]).encode())]):
            self.assertEqual(release.verify_remote(self.source, self.output, release.REPOSITORY, self.tag, "a" * 40), assets)
        changes = [lambda d: d.update(draft=False), lambda d: d.update(tag_name="v0.2.1"),
                   lambda d: d["assets"].pop(), lambda d: d["assets"].append(d["assets"][0]),
                   lambda d: d["assets"][0].update(digest="sha256:" + "0" * 64),
                   lambda d: d["assets"][0].update(size=1),
                   lambda d: d["assets"][0].update(state="new"),
                   lambda d: d["assets"].__setitem__(0, None)]
        for index, change in enumerate(changes):
            bad = deepcopy(draft)
            change(bad)
            with self.subTest(change=index), self.remote(bad), self.assertRaises(ValueError):
                release.verify_remote(self.source, self.output, release.REPOSITORY, self.tag)


if __name__ == "__main__":
    unittest.main(verbosity=2)
