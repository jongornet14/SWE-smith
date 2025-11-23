import libcst
import pytest
from swesmith.bug_gen.type.python.types import (
    TypeChangeModifier,
    TypeRemoveModifier,
)


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        # Case 7: Variable annotation
        (
            """
def foo():
    x: int = 5
    return x
""",
            [
                "def foo():\n    x: str = 5\n    return x\n",
                "def foo():\n    x: float = 5\n    return x\n",
                "def foo():\n    x: bool = 5\n    return x\n",
            ],
        ),
        # Case 8: No annotations, should not change
        (
            """
def foo(x):
    return x + 1
""",
            [
                "def foo(x):\n    return x + 1\n",
            ],
        ),
    ],
)
def test_type_change_modifier(src, expected_variants):
    """Test that TypeChangeModifier correctly changes type annotations."""
    module = libcst.parse_module(src)
    modifier = TypeChangeModifier(likelihood=1.0, seed=42)
    transformer = modifier.Transformer(modifier)
    modified = module.visit(transformer)
    result = modified.code
    
    # Check if the result matches any of the expected variants
    assert any(result.strip() == variant.strip() for variant in expected_variants), (
        f"Got: {result!r}, expected one of: {expected_variants!r}"
    )


def test_type_change_with_low_likelihood():
    """Test that TypeChangeModifier respects likelihood parameter."""
    src = """
def foo(x: int, y: int, z: int) -> int:
    return x + y + z
"""
    module = libcst.parse_module(src)
    # With likelihood=0, nothing should change
    modifier = TypeChangeModifier(likelihood=0.0, seed=42)
    transformer = modifier.Transformer(modifier)
    modified = module.visit(transformer)
    
    assert modified.code == src


def test_type_change_complex_types():
    """Test TypeChangeModifier with complex nested types."""
    src = """
def foo(items: List[Dict[str, int]]) -> Optional[str]:
    return None
"""
    module = libcst.parse_module(src)
    modifier = TypeChangeModifier(likelihood=1.0, seed=42)
    transformer = modifier.Transformer(modifier)
    modified = module.visit(transformer)
    
    # Should produce some change
    assert modified.code != src
