# Release operations

This guide documents the maintainer workflow for test builds and public Acute
Web releases. The public repository is
[`iiankehn/acute-web-android`](https://github.com/iiankehn/acute-web-android).

## Test builds

Open **Actions → Build Android APK → Run workflow**. Use the pinned 40-character
Mozilla commit unless a different upstream revision is being evaluated.

Manual runs produce a debug-signed APK and tablet smoke-test evidence. They do
not receive the production signing secrets and do not publish a release.

## Signed releases

Before publishing, confirm that the release-signing environment described in
[SIGNING.md](SIGNING.md) is configured and that device acceptance testing is
complete.

Create and push an annotated semantic-version tag:

```bash
git tag -a v0.3.1 -m "Acute Web 0.3.1"
git push origin v0.3.1
```

The release workflow:

1. checks out the pinned Mozilla source revision;
2. applies and validates the Acute overlay;
3. builds the ARM64 APK without access to production signing secrets;
4. runs the Android smoke-test matrix;
5. signs the APK in an isolated job;
6. verifies the signing certificate against the established release identity;
7. publishes the APK, checksum, signing report, permissions report, build
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
