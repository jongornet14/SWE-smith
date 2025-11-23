# Type Bug Generation

This module provides procedural bug generators that introduce type-related errors into Python code by modifying type annotations.

## Overview

Type bugs are introduced by mutating type annotations in function signatures, variable declarations, and return types. These modifications create subtle type mismatches that can break code at runtime or cause type checker failures.

### Modifiers

#### `TypeChangeModifier`
Changes existing type annotations to incompatible types. Examples:
- `int` → `str`, `float`, `bool`
- `List[int]` → `List[str]`, `List[float]`, `List[bool]`
- `Dict[str, int]` → `Dict[int, int]`, `Dict[str, str]`, etc.
- `Optional[str]` → `str` (removes Optional wrapper)

## Installation

The type bug generation module uses the same installation as SWE-smith. Install from source:

```bash
git clone https://github.com/SWE-bench/SWE-smith.git
cd SWE-smith
pip install -e .
```

## Usage

### Generate Type Bugs for a Repository

Use the procedural bug generation script to generate type bugs:

```bash
python -m swesmith.bug_gen.type.types <repo_name> --seed 42 --max_bugs 100
```

Example:

```bash
python -m swesmith.bug_gen.type.types django/django --seed 42 --max_bugs 50
```

This will:
1. Clone the specified repository
2. Extract code entities (functions, classes, methods)
3. Apply type modifiers to eligible entities
4. Generate bug patches and metadata
5. Save results to `logs/bug_gen/<repo_name>/`

### Command Line Options

- `repo` - Name of a SWE-smith repository to generate bugs for (required)
- `--seed` - Random seed for reproducibility (default: 24)
- `--max_bugs` - Maximum number of bugs per modifier (default: -1, unlimited)
- `--interleave` - Randomize order of modifiers instead of sequential processing

### Programmatic Usage

```python
import libcst as cst
from swesmith.bug_gen.type.python.types import TypeChangeModifier

# Parse Python code
code = """
def calculate(x: int, y: int) -> int:
    return x + y
"""
module = cst.parse_module(code)

# Apply type mutation
modifier = TypeChangeModifier(likelihood=1.0, seed=42)
transformer = modifier.Transformer(modifier)
modified = module.visit(transformer)

print(modified.code)
# Output: def calculate(x: str, y: str) -> str:
#             return x + y
```

### Configuration

Type modifiers can be configured in `swesmith/bug_gen/type/python/__init__.py`:

```python
MODIFIERS_PYTHON_TYPE: list[ProceduralModifier] = [
    TypeChangeModifier(likelihood=0.3),  # 30% chance per annotation
    TypeRemoveModifier(likelihood=0.2),  # 20% chance per annotation
]
```

## Output

Generated bugs are saved to `logs/bug_gen/<repo_name>/<entity_path>/`:

### Files per Bug
- `metadata__<modifier>__<hash>.json` - Bug metadata including explanation and strategy
- `bug__<modifier>__<hash>.diff` - Git diff showing the code changes

### Example Metadata
```json
{
  "rewrite": "def foo(x: str) -> str:\n    return x + 1\n",
  "explanation": "Introduced type mutation bug.",
  "strategy": "type_change"
}
```

## Implementation Details

### Type Mutations

**Primitive Types:**
- Mutates to: `str`, `float`, `bool`

**Generic Types:**
- `List[T]` - Changes inner type T
- `Dict[K, V]` - Changes either key K or value V type
- `Optional[T]` - Unwraps to just T

**Dict Key Mutations:**
- Mutates to: `int`, `bytes`, `list`

### How It Works

1. **AST Traversal**: Uses libcst to traverse the Abstract Syntax Tree
2. **Annotation Detection**: Identifies all `Annotation` nodes (parameters, returns, variables)
3. **Probabilistic Mutation**: Each annotation has `likelihood` chance of being mutated
4. **Type Replacement**: Replaces annotation with a randomly chosen incompatible type
5. **Code Generation**: Reconstructs Python code from modified AST

### Eligible Code Entities

Type modifiers target:
- Function parameters with type annotations
- Function return types
- Variable annotations (e.g., `x: int = 5`)
- Generic type parameters (List, Dict, Optional, etc.)

## Testing

Run the test suite:

```bash
pytest tests/bug_gen/type/python/test_py_types.py -v
```

## Examples

### Before
```python
def process_items(items: List[int]) -> Dict[str, int]:
    result = {}
    for item in items:
        result[str(item)] = item * 2
    return result
```

### After (TypeChangeModifier)
```python
def process_items(items: List[str]) -> Dict[int, str]:
    result = {}
    for item in items:
        result[str(item)] = item * 2
    return result
```

This creates a type mismatch where the function expects `List[str]` but performs integer operations, and returns `Dict[int, str]` instead of `Dict[str, int]`.

## Limitations

- Only supports Python code (`.py` files)
- Requires existing type annotations to modify
- Does not validate if mutations are semantically meaningful
- May generate invalid code if mutations conflict with runtime logic
