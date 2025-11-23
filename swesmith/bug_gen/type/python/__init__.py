from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.bug_gen.type.python.types import (
    TypeChangeModifier,
    TypeRemoveModifier,
)

MODIFIERS_PYTHON_TYPE: list[ProceduralModifier] = [
    TypeChangeModifier(likelihood=0.3),
    TypeRemoveModifier(likelihood=0.2),
]
