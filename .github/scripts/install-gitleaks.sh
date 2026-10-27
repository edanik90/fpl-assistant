#!/usr/bin/env bash
set -euo pipefail

# Direct CLI use avoids the separate Gitleaks Action's licensing/telemetry setup.
# Update version and checksums together from the official release.
version=8.30.1
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64)
    platform=linux_x64
    checksum=551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb ;;
  Linux-aarch64)
    platform=linux_arm64
    checksum=e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080 ;;
  Darwin-arm64)
    platform=darwin_arm64
    checksum=b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5 ;;
  *) echo "Unsupported Gitleaks installer platform" >&2; exit 1 ;;
esac

install_dir="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/fpl-security-tools/gitleaks-$version"
mkdir -p "$install_dir"
archive="$install_dir/gitleaks.tar.gz"
curl --fail --silent --show-error --location --retry 3 \
  "https://github.com/gitleaks/gitleaks/releases/download/v$version/gitleaks_${version}_${platform}.tar.gz" \
  --output "$archive"
if command -v sha256sum >/dev/null 2>&1; then
  printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check --status
else
  printf '%s  %s\n' "$checksum" "$archive" | shasum --algorithm 256 --check --status
fi
tar -xzf "$archive" -C "$install_dir" gitleaks
if [[ -n "${GITHUB_PATH:-}" ]]; then
  printf '%s\n' "$install_dir" >> "$GITHUB_PATH"
fi
printf 'Gitleaks installed: %s/gitleaks\n' "$install_dir"
