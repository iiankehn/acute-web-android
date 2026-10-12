# Android 2.0 dependency findings — October 12, 2026

Status: release acceptance is blocked pending vulnerability triage. This does not establish a
remote exploit against Acute. Build 88 remains an experimental validation build, not an accepted release.

OSV queries completed for 709 unique versions from Firefox commit
`0c469c2352451630bc69fc328c9f0c589c6c534d`: 154 Maven catalog coordinates and
555 registry crates in the complete Firefox Cargo.lock. None of the 154 catalog Maven versions
returned an advisory. This is not a resolved-transitive Maven scan and excludes local/git crates;
Cargo.lock includes build/test and non-Android packages as well as Android dependencies.

| Package | Pinned version | Advisory | Classification / next action |
|---|---|---|---|
| smallbitvec | 2.5.1 | [GHSA-97wc-2hqc-cjgr](https://github.com/servo/smallbitvec/security/advisories/GHSA-97wc-2hqc-cjgr) | Memory corruption; release blocker pending Android call-path and artifact review |
| serde_with | 3.12.0 | [GHSA-7gcf-g7xr-8hxj](https://github.com/jonasbb/serde_with/security/advisories/GHSA-7gcf-g7xr-8hxj) | Serialization panic; inspect `KeyValueMap` use and compiled targets |
| ringbuf | 0.2.8 | [RUSTSEC-2026-0293](https://rustsec.org/advisories/RUSTSEC-2026-0293.html) | Panic-related memory corruption; lockfile parents are CoreAudio/PulseAudio backends; Android reachability not established |
| bincode | 1.3.3 | [RUSTSEC-2025-0141](https://rustsec.org/advisories/RUSTSEC-2025-0141.html) | Unmaintained notice; track upstream maintenance, not a confirmed vulnerability |
| paste | 1.0.11 | [RUSTSEC-2024-0436](https://rustsec.org/advisories/RUSTSEC-2024-0436.html) | Unmaintained notice; build-time macro dependency |
| unsafe-libyaml | 0.2.11 | [RUSTSEC-2024-0449](https://rustsec.org/advisories/RUSTSEC-2024-0449.html) | Unmaintained notice; trace serde_yaml build/runtime use |

## Verified source evidence

At the pinned Firefox commit, `third_party/rust/smallbitvec/src/lib.rs` still computes buffer capacity
with the unchecked addition described in the maintainer advisory. Its lockfile consumers include
`style`, `malloc_size_of`, `to_shmem` and `dogear`; this is not dismissible solely as a desktop/test crate.
The maintainer lists 2.6.1 as patched, but changing the lockfile alone would not patch Acute's downloaded
Gecko binary. The artifact build consumes Mozilla's precompiled native libraries. Remediation must use
an upstream native artifact with a verified fix, or a validated full native rebuild/backport.

The vendored serde_with implementation also contains the affected subtraction. The recorded parent is
qlog, whose inspected root file uses `skip_serializing_none`; that inspection does not prove absence of
`KeyValueMap` elsewhere. Maintain the finding until its full target/call-path analysis completes.

Do not replace versions blindly, assert that all six findings are exploitable, or dismiss memory-safety
findings based only on upstream's latest release label. Retain Stable/Beta and the migration archive.

## Reproduce and interpret

Download `gradle/libs.versions.toml` and `Cargo.lock` from the immutable Firefox commit above, then run:

```sh
python3 scripts/audit_dependencies.py --catalog /path/to/libs.versions.toml --cargo /path/to/Cargo.lock --report /path/to/report.json
```

Exit 0: completed inventory scan with no vulnerability records; maintenance notices may remain.
Exit 1: completed scan with unresolved vulnerability records. Exit 2: incomplete scan/network/input error.
The scanner handles batch pagination and rejects partial/malformed responses. Only public dependency
coordinates go to OSV. Reports describe inventory findings; they do not prove runtime reachability.

The new compiled-manifest verifier audits dependency-merged APKs for channel identity, Android 12,
backup/debug/UID boundaries, prohibited permissions, and non-exported isolated provider authorities.
Its output also inventories exported entry points for manual handler review. It has six regression
cases; an actual Build 88 APK has not yet been checked with it. No APK pipeline change is merged while
that build is in progress.
