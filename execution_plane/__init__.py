"""SEOS Controlled Execution Plane V1.

This package is the bounded worker side of SEOS. It is deliberately separate
from the governance control plane and only runs work after an explicit
execution permit has been validated.
"""

from __future__ import annotations

SCHEMA_VERSION = "seos_execution_plane_v1"

