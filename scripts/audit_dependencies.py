#!/usr/bin/env python3
"""Query OSV for pinned Rust registry and Maven catalog versions.

This inventories source metadata, not the resolved Android runtime graph or
prebuilt Gecko binaries. Findings require platform and vendored-patch triage.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request
import tomllib


API = "https://api.osv.dev/v1/querybatch"


def inventory(source):
    files = {"Cargo.lock": source / "Cargo.lock", "gradle/libs.versions.toml": source / "gradle/libs.versions.toml"}
    raw = {name: path.read_bytes() for name, path in files.items()}
    cargo = tomllib.loads(raw["Cargo.lock"].decode("utf-8"))
    catalog = tomllib.loads(raw["gradle/libs.versions.toml"].decode("utf-8"))
    queries, omitted = [], []
    for package in cargo["package"]:
        if package.get("source") in {"registry+https://github.com/rust-lang/crates.io-index", "sparse+https://index.crates.io/"}:
            queries.append({"package": {"ecosystem": "crates.io", "name": package["name"]}, "version": package["version"]})
        else:
            omitted.append({"ecosystem": "Rust", "name": package["name"], "reason": "local, Git or non-crates.io registry source"})
    for alias, package in catalog.get("libraries", {}).items():
        if not isinstance(package, dict):
            omitted.append({"ecosystem": "Maven", "name": alias, "reason": "unsupported catalog notation"})
            continue
        name = package.get("module") or f"{package.get('group', '')}:{package.get('name', '')}"
        version = package.get("version")
        if isinstance(version, dict):
            version = catalog["versions"].get(version.get("ref"))
        if not isinstance(version, str) or name.count(":") != 1 or not all(name.split(":")):
            omitted.append({"ecosystem": "Maven", "name": alias, "reason": "no explicit module/version"})
            continue
        queries.append({"package": {"ecosystem": "Maven", "name": name}, "version": version})
    queries = list({(q["package"]["ecosystem"], q["package"]["name"], q["version"]): q for q in queries}.values())
    return queries, {name: hashlib.sha256(data).hexdigest() for name, data in raw.items()}, omitted


def post(queries):
    request = urllib.request.Request(API, data=json.dumps({"queries": queries}).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Acute-source-dependency-audit"})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read(32 * 1024 * 1024 + 1)
        if len(data) > 32 * 1024 * 1024:
            raise ValueError("OSV response exceeded size limit")
        return json.loads(data)


def scan(queries, request=post):
    entries = []
    for offset in range(0, len(queries), 100):
        batch = queries[offset:offset + 100]
        results = request(batch).get("results")
        if not isinstance(results, list) or len(results) != len(batch):
            raise ValueError("Incomplete OSV response; scan is not accepted")
        for query, result in zip(batch, results):
            if not isinstance(result, dict):
                raise ValueError("Malformed OSV result; scan is not accepted")
            if "error" in result:
                raise ValueError("OSV returned a per-package error")
            # Do not silently discard findings beyond OSV's per-query page limit.
            if result.get("next_page_token"):
                raise ValueError("Paginated OSV result; complete per-package triage is required")
            vulns = result.get("vulns", [])
            if not isinstance(vulns, list) or any(not isinstance(v, dict) or not v.get("id") for v in vulns):
                raise ValueError("Malformed OSV advisory list")
            entries.append({"query": query, "advisories": vulns})
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Firefox checkout at the reviewed immutable pin")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        queries, hashes, omitted = inventory(args.source)
        if not queries:
            raise ValueError("Empty dependency inventory")
        entries = scan(queries)
        report = {"generated_utc": datetime.now(timezone.utc).isoformat(), "source_sha256": hashes,
                  "scope": "Rust registry lockfile and explicit Maven catalog versions; not resolved APK dependencies",
                  "omitted": omitted, "entries": entries}
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Dependency audit failed: {error}\n")
    matched = sum(bool(entry["advisories"]) for entry in entries)
    print(f"Scanned {len(entries)} package versions; {matched} require advisory triage; {len(omitted)} omitted inputs")
    return 2 if matched else 0


if __name__ == "__main__":
    raise SystemExit(main())
