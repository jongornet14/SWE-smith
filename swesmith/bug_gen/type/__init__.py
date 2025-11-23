"""
Type-related bug generation.

This module provides bug generators that modify type annotations and type-related code.
"""

from swesmith.bug_gen.type.python import MODIFIERS_PYTHON_TYPE

MAP_EXT_TO_TYPE_MODIFIERS = {
    ".py": MODIFIERS_PYTHON_TYPE,
}
