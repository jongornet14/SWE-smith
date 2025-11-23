import libcst
import pytest
from swesmith.bug_gen.type.python.types import (
    TypeChangeModifier,
    TypeRemoveModifier,
)


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        # Case 1: Change simple parameter type
        (
            """
def foo(x: int) -> int:
    return x + 1
""",
            [
                "def foo(x: str) -> int:\n    return x + 1\n",
                "def foo(x: float) -> int:\n    return x + 1\n",
                "def foo(x: bool) -> int:\n    return x + 1\n",
            ],
        ),
        # Case 2: Change return type
        (
            """
def bar(x: int) -> str:
    return str(x)
""",
            [
                "def bar(x: int) -> int:\n    return str(x)\n",
                "def bar(x: int) -> bytes:\n    return str(x)\n",
                "def bar(x: int) -> list:\n    return str(x)\n",
            ],
        ),
        # Case 3: Change List generic parameter
        (
            """
def baz(items: List[int]) -> None:
    pass
""",
            [
                "def baz(items: List[str]) -> None:\n    pass\n",
                "def baz(items: List[float]) -> None:\n    pass\n",
                "def baz(items: List[bool]) -> None:\n    pass\n",
            ],
        ),
        # Case 4: Remove Optional wrapper
        (
            """
def qux(value: Optional[str]) -> None:
    pass
""",
            [
                "def qux(value: str) -> None:\n    pass\n",
            ],
        ),
        # Case 5: Change Dict key type
        (
            """
def process(data: Dict[str, int]) -> None:
    pass
""",
            [
                "def process(data: Dict[int, int]) -> None:\n    pass\n",
                "def process(data: Dict[bytes, int]) -> None:\n    pass\n",
                "def process(data: Dict[list, int]) -> None:\n    pass\n",
            ],
        ),
        # Case 6: Change Dict value type
        (
            """
def process(data: Dict[str, int]) -> None:
    pass
""",
            [
                "def process(data: Dict[str, str]) -> None:\n    pass\n",
                "def process(data: Dict[str, float]) -> None:\n    pass\n",
                "def process(data: Dict[str, bool]) -> None:\n    pass\n",
            ],
        ),
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


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        # Case 1: Remove parameter annotation
        (
            """
def foo(x: int) -> int:
    return x + 1
""",
            [
                "def foo(x) -> int:\n    return x + 1\n",
            ],
        ),
        # Case 2: Remove return type annotation
        (
            """
def bar(x: int) -> str:
    return str(x)
""",
            [
                "def bar(x: int):\n    return str(x)\n",
            ],
        ),
        # Case 3: Remove both parameter and return annotations
        (
            """
def baz(x: int, y: str) -> bool:
    return len(y) > x
""",
            [
                "def baz(x, y: str) -> bool:\n    return len(y) > x\n",
                "def baz(x: int, y) -> bool:\n    return len(y) > x\n",
                "def baz(x: int, y: str):\n    return len(y) > x\n",
            ],
        ),
        # Case 4: Convert annotated assignment to regular assignment
        (
            """
def foo():
    x: int = 5
    return x
""",
            [
                "def foo():\n    x = 5\n    return x\n",
            ],
        ),
        # Case 5: Multiple parameter annotations
        (
            """
def process(a: int, b: str, c: float) -> None:
    pass
""",
            [
                "def process(a, b: str, c: float) -> None:\n    pass\n",
                "def process(a: int, b, c: float) -> None:\n    pass\n",
                "def process(a: int, b: str, c) -> None:\n    pass\n",
                "def process(a: int, b: str, c: float):\n    pass\n",
            ],
        ),
        # Case 6: No annotations, should not change
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
def test_type_remove_modifier(src, expected_variants):
    """Test that TypeRemoveModifier correctly removes type annotations."""
    module = libcst.parse_module(src)
    modifier = TypeRemoveModifier(likelihood=1.0, seed=42)
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


def test_type_remove_with_low_likelihood():
    """Test that TypeRemoveModifier respects likelihood parameter."""
    src = """
def foo(x: int, y: int) -> int:
    return x + y
"""
    module = libcst.parse_module(src)
    # With likelihood=0, nothing should change
    modifier = TypeRemoveModifier(likelihood=0.0, seed=42)
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


def test_type_change_modifier_via_modify_method():
    """Test using the full modify() method instead of just the transformer."""
    from swesmith.constants import CodeEntity, CodeProperty
    
    src_code = """def add(x: int, y: int) -> int:
    return x + y
"""
    
    # Create a mock CodeEntity
    class MockCodeEntity:
        def __init__(self, src_code):
            self.src_code = src_code
            self._tags = {CodeProperty.IS_FUNCTION}
            self.complexity = 5
    
    entity = MockCodeEntity(src_code)
    modifier = TypeChangeModifier(likelihood=1.0, seed=42)
    
    # Check that entity passes the can_change check
    assert modifier.can_change(entity)
    
    # Apply the modifier
    result = modifier.modify(entity)
    
    # Should produce a BugRewrite
    assert result is not None
    assert result.rewrite != src_code
    assert result.explanation == "The type annotations in the code are likely incorrect."
    assert result.strategy == "func_pm_type_change"


def test_type_remove_modifier_via_modify_method():
    """Test TypeRemoveModifier using the full modify() method."""
    from swesmith.constants import CodeEntity, CodeProperty
    
    src_code = """def add(x: int, y: int) -> int:
    return x + y
"""
    
    # Create a mock CodeEntity
    class MockCodeEntity:
        def __init__(self, src_code):
            self.src_code = src_code
            self._tags = {CodeProperty.IS_FUNCTION}
            self.complexity = 5
    
    entity = MockCodeEntity(src_code)
    modifier = TypeRemoveModifier(likelihood=1.0, seed=42)
    
    # Apply the modifier
    result = modifier.modify(entity)
    
    # Should produce a BugRewrite
    assert result is not None
    assert result.rewrite != src_code
    assert result.explanation == "There are missing type annotations in the code."
    assert result.strategy == "func_pm_type_remove"
