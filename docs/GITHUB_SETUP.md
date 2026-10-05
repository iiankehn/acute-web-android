# Release operations

This guide documents the maintainer workflow for test builds and public Acute
Web releases. The public repository is
[`iiankehn/acute-web-android`](https://github.com/iiankehn/acute-web-android).

## Test builds

Open **Actions → Build Android APK → Run workflow**. Use the pinned 40-character
Mozilla commit unless a different upstream revision is being evaluated.

Manual runs produce unsigned/debug-signed ARM64 and x86_64 artifacts for engineering
inspection. They do not receive the production signing secrets and do not
publish a release.

## Signed releases

Before publishing, confirm that the release-signing environment described in
[SIGNING.md](SIGNING.md) is configured and that device acceptance testing is
complete.

Create and push an annotated semantic-version tag:

```bash
VERSION=MAJOR.MINOR.PATCH
git tag -a "v${VERSION}" -m "Acute Web ${VERSION}"
git push origin "v${VERSION}"
```

The release workflow:

1. runs the complete Acute source and release-control audit;
2. checks out the pinned Mozilla source revision;
3. applies and validates the Acute overlay;
4. builds and verifies the ARM64 and x86_64 APKs without production signing secrets;
5. signs both APKs in isolated jobs;
6. verifies the signing certificate against the established release identity;
7. publishes the APKs, checksums, signing reports, permissions reports, build
   inputs, and provenance attestation to GitHub Releases.

Do not replace published APKs under an existing version tag. Corrections should
use a new patch version so users and auditors can identify the exact artifact.

## Release checklist

- Update the version-specific release notes.
- Run the overlay test suite.
- Review changes against the pinned upstream source.
- Complete phone and tablet acceptance checks.
- Confirm the APK is signed with the production certificate.
- Verify the SHA-256 checksum and that every release asset is non-empty.
- Install the release over the previous production version.
- Verify the in-app update flow and direct download link.
- Update the public website to the new stable version.

## Repository protections

- Keep the default GitHub Actions token permission read-only. Grant write
  access only to the publishing job.
- Protect the `main` branch and require validation checks.
- Restrict creation of tags matching `v*`.
- Protect the `release-signing` environment and require review when supported.
- Enable GitHub private vulnerability reporting.
- Never expose release secrets to pull-request or upstream build jobs.
