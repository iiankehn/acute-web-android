# Contributing to Acute Web

Thanks for helping improve Acute Web by CORE. Contributions should preserve the
project's distinct identity, privacy position, and reliable sideloaded update
path while respecting the licenses and attribution of upstream Mozilla code.

## Report a bug

Use [GitHub Issues](https://github.com/iiankehn/acute-web-android/issues) and
search for an existing report first. A useful bug report includes:

- Acute Web version;
- Android version, device model, and CPU architecture;
- whether the problem occurs in normal or private browsing;
- exact reproduction steps;
- expected and observed results;
- relevant logs or screenshots with personal data removed.

Security vulnerabilities must follow [SECURITY.md](SECURITY.md), not the public
issue tracker.

## Propose a change

Open an issue before investing in a large feature or architectural change.
Describe the user problem, proposed behavior, privacy implications, and how the
change should work on both phones and tablets.

## Development workflow

1. Fork the repository and create a focused branch.
2. Make the smallest coherent change.
3. Add or update overlay fixtures and regression tests.
4. Run the lightweight test suite locally.
5. Use a manual GitHub Actions build for full APK and tablet smoke testing.
6. Test the resulting APK on a physical device when behavior changes.
7. Open a pull request that explains the change, risk, and validation performed.

Do not commit generated APKs, keystores, credentials, Mozilla source trees, or
build output.

## Project standards

Contributions should:

- use **Acute Web** for the product and **Acute Web by CORE** where parent-brand
  attribution is appropriate;
- avoid Firefox product branding outside accurate legal, licensing, source, or
  technical disclosures;
- keep telemetry, diagnostic submission, crash uploading, and marketing
  surfaces disabled unless maintainers approve a documented policy change;
- preserve the signed GitHub Releases update model;
- keep upstream patches fail-closed and reviewable;
- support Android phone and tablet layouts;
- include accessible text, controls, and contrast;
- retain all required upstream copyright and license notices.

## License

By contributing, you agree that your contribution may be distributed under the
[Mozilla Public License 2.0](LICENSE). Files derived from Mozilla code retain
their applicable original notices and terms.
