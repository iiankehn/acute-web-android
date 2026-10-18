#!/usr/bin/env bash
# Run before building or exposing signing credentials. Never accept a release
# tag merely because its name looks like a version.
set -euo pipefail
if [[ "$GITHUB_REF" != refs/tags/* ]]; then
  exit 0
fi
if [[ "$GITHUB_REF" =~ ^refs/tags/v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  release_branch=main
elif [[ "$GITHUB_REF" =~ ^refs/tags/v[0-9]+\.[0-9]+\.[0-9]+-beta\.[0-9]+$ ]]; then
  release_branch=beta
else
  echo '::error::Unsupported release tag'
  exit 1
fi
# Fetch only the required branch, with full ancestry even in a shallow checkout.
fetch_options=()
if [[ "$(git rev-parse --is-shallow-repository)" == true ]]; then
  fetch_options+=(--unshallow)
fi
git fetch --no-tags "${fetch_options[@]}" origin "+refs/heads/${release_branch}:refs/remotes/origin/${release_branch}"
tag_commit="$(git rev-parse "${GITHUB_REF}^{commit}")"
checkout_commit="$(git rev-parse 'HEAD^{commit}')"
if [[ "$tag_commit" != "$checkout_commit" ]] || ! git merge-base --is-ancestor "$tag_commit" "refs/remotes/origin/${release_branch}"; then
  echo "::error::Release tag must identify the checked-out commit on ${release_branch}"
  exit 1
fi
printf 'Verified %s (%s) belongs to %s\n' "$GITHUB_REF" "$tag_commit" "$release_branch"
