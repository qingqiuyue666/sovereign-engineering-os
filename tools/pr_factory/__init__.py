"""PR factory scaffold tooling."""

from tools.pr_factory.generate_capability_scaffold import (
    CapabilityScaffoldConfig,
    ScaffoldCollisionError,
    generate_scaffold,
)

__all__ = [
    "CapabilityScaffoldConfig",
    "ScaffoldCollisionError",
    "generate_scaffold",
]
