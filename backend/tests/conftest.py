"""Shared pytest configuration for CloudDesk tests."""

import sys
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]

SHARED_LAYER_DIRECTORY = BACKEND_DIRECTORY / "layers" / "shared" / "python"


# Lambda handler directories should be importable.
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))


# Add the shared layer after local Python site-packages.
#
# This lets tests import `shared.*`, while ensuring Windows-compatible
# development dependencies such as psycopg are selected before the
# Linux packages bundled for AWS Lambda.
if str(SHARED_LAYER_DIRECTORY) not in sys.path:
    sys.path.append(str(SHARED_LAYER_DIRECTORY))
