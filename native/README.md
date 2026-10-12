# Acute native GeckoView foundation

Development prototype on `dev`. The preserved Fenix
implementation remains in the repository. See [migration baseline](../docs/NATIVE_MIGRATION.md)
for source checkpoints, parity requirements, risks and subsequent work.

Build with Java 17 and Android SDK 37 (Build Tools 36.0.0):

```sh
cd native
./gradlew :browser-core:test :app:lintDebug :app:assembleDebug
```

The preview uses a separate app ID and debug signer. It provides one web session,
search/navigation and an independent native toolbar. Existing tabs, profiles,
passwords, Sync, extensions and downloads are not migrated in this slice.
The GitHub native-foundation workflow produces a development APK; it does not
publish or sign a production release. Physical-device testing is required.

CI debug keys are ephemeral: successive artifacts are not guaranteed to install
over one another. CI uses the workflow run number as its version code. A persistent isolated dev signer
is required before ongoing device testing; never uninstall Stable/Beta for Dev.
