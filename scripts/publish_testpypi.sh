#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-check}"

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "Python is required"
  exit 1
fi

if [[ "$TARGET" != "check" && "$TARGET" != "test" && "$TARGET" != "prod" && "$TARGET" != "all" ]]; then
  echo "Usage: scripts/publish_testpypi.sh [check|test|prod|all]"
  exit 1
fi

VERSION="$(grep -E '^version\s*=\s*"' pyproject.toml | head -n 1 | sed -E 's/^version\s*=\s*"([^"]+)"/\1/')"
if [[ -z "$VERSION" ]]; then
  echo "Cannot read version from pyproject.toml"
  exit 1
fi
TAG="v${VERSION}"

if ! git rev-parse --verify "$TAG" >/dev/null 2>&1; then
  echo "Missing git tag $TAG"
  exit 1
fi

if [[ "$(git rev-list -n 1 "$TAG")" != "$(git rev-parse HEAD)" ]]; then
  echo "Tag $TAG does not point to HEAD"
  exit 1
fi

$PYTHON_BIN -m pip install --upgrade pip
$PYTHON_BIN -m pip install twine

if ! ls dist/* >/dev/null 2>&1; then
  echo "Missing dist artifacts. Download CI artifact first."
  exit 1
fi

$PYTHON_BIN -m twine check dist/*

upload_test() {
  : "${TWINE_USERNAME:?TWINE_USERNAME is required}"
  : "${TWINE_PASSWORD_TESTPYPI:?TWINE_PASSWORD_TESTPYPI is required}"
  TWINE_PASSWORD="$TWINE_PASSWORD_TESTPYPI" $PYTHON_BIN -m twine upload --repository testpypi dist/*
}

upload_prod() {
  : "${TWINE_USERNAME:?TWINE_USERNAME is required}"
  : "${TWINE_PASSWORD_PYPI:?TWINE_PASSWORD_PYPI is required}"
  TWINE_PASSWORD="$TWINE_PASSWORD_PYPI" $PYTHON_BIN -m twine upload dist/*
}

if [[ "$TARGET" == "check" ]]; then
  exit 0
elif [[ "$TARGET" == "test" ]]; then
  upload_test
elif [[ "$TARGET" == "prod" ]]; then
  upload_prod
else
  upload_test
  upload_prod
fi
