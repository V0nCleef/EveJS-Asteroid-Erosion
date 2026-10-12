# Releasing Asteroid Erosion

Every public version needs its ZIP **and** matching Launcher `.update.json`.
Do not upload a ZIP alone or replace an already released version's bytes.

1. Implement and review the change. Update the manifest version, client READY
   marker, README and verification evidence.
2. Run focused native/client checks and GridCheck against a disposable Native
   tree. Verify the rendered menu for UI changes. Keep proprietary client
   references, local fixtures, credentials and recordings outside Git.
3. Add `releases/<version>.md` with version-specific notes and any migration
   instructions. Retain `updates.preserveFiles: ["config.json"]` and the native
   per-character preferences key for compatible updates.
4. From the repository root, run:

   ```text
   python tools/test_release.py
   python tools/release.py build --tag v<version> --output release-dist
   python tools/release.py verify --tag v<version> --output release-dist
   ```

5. Inspect the source diff and ZIP. Commit the checked source, push it, then push
   the matching `v<version>` tag. Watch **Publish checked mod release** in Actions.

The workflow checks the manifest, tag, update source, settings preservation,
menu contract, minimum Launcher version and release notes before uploading. It
creates an unpublished draft containing the ZIP, metadata and checksums, checks
GitHub's uploaded names/sizes/digests, downloads the assets and compares every
byte with the checked source, then publishes.

An existing release is refused. A failed upload/verification leaves a draft;
inspect that draft and repair the failure deliberately. Do not publish it
manually without completing the same verification. For a correction to a
published package, bump the version and make a new release.

The builder uses a fixed public-file list and deterministic ZIP metadata.
Release tools, tests, workflow, notes and demo assets are not included in the
installable mod. Changing the server/API/update contract requires reviewing the
builder and migration plan together; its rejection is intentional.
