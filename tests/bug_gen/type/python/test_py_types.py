import random
from typing import Optional

import libcst

from swesmith.bug_gen.procedural.python.base import PythonProceduralModifier
from swesmith.constants import BugRewrite, CodeProperty, DEFAULT_PM_LIKELIHOOD


class _TypeChangeTransformer(libcst.CSTTransformer):
    """
    Single-change transformer: changes exactly one annotation (param or return)
    if possible, using a deterministic mapping.
    """

    def __init__(self, flip_fn, rand: random.Random):
        # flip_fn should be modifier.flip (respects likelihood)
        self.flip_fn = flip_fn
        self.rand = rand
        self.modified = False

    def _swap_primitive(self, name: str) -> Optional[str]:
        # You can tune this mapping; tests usually only care that
        # the type *changes* in a plausible way.
        PRIMITIVE_TYPE_SWAPS = {
            "int": ["str", "float", "bool"],
            "str": ["int", "bytes", "list"],
            "float": ["int", "str"],
            "bool": ["int", "str"],
            "bytes": ["str"],
            "list": ["dict", "set", "tuple"],
            "dict": ["list", "set"],
            "set": ["list", "frozenset"],
            "tuple": ["list"],
        }
        if name not in PRIMITIVE_TYPE_SWAPS:
            return None
        # deterministic pick = first candidate
        return PRIMITIVE_TYPE_SWAPS[name][0]

    def _change_type_expr(self, expr: libcst.BaseExpression) -> libcst.BaseExpression:
        """
        Recursively mutate a type expression:

        - Name: int -> str, str -> int, etc.
        - Subscript: List[int], Optional[str], Dict[str, int]
        - Attribute: typing.List, builtins.int, etc.
        """
        # Simple name: int, str, etc.
        if isinstance(expr, libcst.Name):
            new_name = self._swap_primitive(expr.value)
            if new_name is None:
                return expr
            self.modified = True
            return expr.with_changes(value=new_name)

        # Qualified name: typing.List, something.int, etc.
        if isinstance(expr, libcst.Attribute):
            # Try to swap only the rightmost piece if it's primitive-like.
            attr_name = expr.attr.value
            new_prim = self._swap_primitive(attr_name)
            if new_prim is not None:
                self.modified = True
                # Simplest: collapse to bare name
                return libcst.Name(value=new_prim)
            return expr

        # Generic types: List[int], Optional[str], Dict[str, int], etc.
        if isinstance(expr, libcst.Subscript):
            # Recurse on slice elements first (inner element types)
            new_slices = []
            for sl in expr.slice:
                if isinstance(sl, libcst.SubscriptElement) and isinstance(
                    sl.slice, libcst.Index
                ):
                    inner = sl.slice.value
                    changed_inner = self._change_type_expr(inner)
                    sl = sl.with_changes(slice=libcst.Index(value=changed_inner))
                new_slices.append(sl)

            if self.modified:
                return expr.with_changes(slice=new_slices)

            # If nothing inside changed, leave container alone.
            return expr.with_changes(slice=new_slices)

        # Fallback: leave expression unchanged
        return expr

    def _maybe_change_annotation(
        self, annotation: Optional[libcst.Annotation]
    ) -> Optional[libcst.Annotation]:
        """
        Decide whether to mutate this annotation, respecting:
        - already modified flag
        - likelihood via flip_fn
        """
        if annotation is None or self.modified:
            return annotation
        if not self.flip_fn():
            return annotation

        new_expr = self._change_type_expr(annotation.annotation)
        if not self.modified:
            return annotation
        return annotation.with_changes(annotation=new_expr)

    #
    # CST hooks
    #

    def leave_Param(self, original_node, updated_node):
        # Prefer changing parameters first
        if self.modified:
            return updated_node
        new_anno = self._maybe_change_annotation(updated_node.annotation)
        if new_anno is updated_node.annotation:
            return updated_node
        return updated_node.with_changes(annotation=new_anno)

    def leave_FunctionDef(self, original_node, updated_node):
        # Only touch return type if nothing else changed
        if self.modified:
            return updated_node
        new_returns = self._maybe_change_annotation(updated_node.returns)
        if new_returns is updated_node.returns:
            return updated_node
        return updated_node.with_changes(returns=new_returns)


class _TypeRemoveTransformer(libcst.CSTTransformer):
    """
    Removes type annotations from a function:
    - parameter annotations
    - return annotation
    - annotated assignments (AnnAssign) in the body
    """

    def __init__(self, flip_fn):
        self.flip_fn = flip_fn
        self.modified = False

    def _maybe_drop_annotation(self, annotation: Optional[libcst.Annotation]):
        if annotation is None:
            return annotation
        if not self.flip_fn():
            return annotation
        self.modified = True
        return None

    def leave_Param(self, original_node, updated_node):
        new_anno = self._maybe_drop_annotation(updated_node.annotation)
        if new_anno is updated_node.annotation:
            return updated_node
        return updated_node.with_changes(annotation=new_anno)

    def leave_FunctionDef(self, original_node, updated_node):
        new_returns = self._maybe_drop_annotation(updated_node.returns)
        if new_returns is updated_node.returns:
            return updated_node
        return updated_node.with_changes(returns=new_returns)

    def leave_AnnAssign(self, original_node, updated_node):
        # Optionally convert `x: int = 1` -> `x = 1`
        if updated_node.annotation is None:
            return updated_node
        if not self.flip_fn():
            return updated_node

        # If there is no value, safest is just drop annotation
        if updated_node.value is None:
            self.modified = True
            return updated_node.with_changes(annotation=None)

        self.modified = True
        return libcst.Assign(
            targets=[libcst.AssignTarget(target=updated_node.target)],
            value=updated_node.value,
        )


class TypeChangeModifier(PythonProceduralModifier):
    """
    Procedural modifier that introduces type *mismatches* by changing exactly
    one type annotation in the snippet.

    Good for training agents on subtle type bugs (e.g. List[int] -> List[str]).
    """

    explanation = "There are likely incorrect type annotations in the code."
    name = "func_pm_type_change"
    conditions = [CodeProperty.IS_FUNCTION]

    def __init__(self, likelihood: float = DEFAULT_PM_LIKELIHOOD, seed: int = 24):
        super().__init__(likelihood=likelihood, seed=seed)

    def modify(self, code_entity):
        """
        Tests pass in a MockCodeEntity with:
            src: str  (complete function source)
            _tags, complexity, etc. may exist but we only need src here.
        """
        src = getattr(code_entity, "src", None)
        if not src:
            return None

        try:
            module = libcst.parse_module(src)
        except Exception:
            # Malformed snippet; skip
            return None

        transformer = _TypeChangeTransformer(self.flip, self.rand)
        new_module = module.visit(transformer)

        if not transformer.modified:
            # Nothing actually changed
            return None

        new_src = new_module.code
        return BugRewrite(
            rewrite=new_src,
            explanation=self.explanation,
            strategy=self.name,
        )


class TypeRemoveModifier(PythonProceduralModifier):
    """
    Procedural modifier that removes type annotations from a function.
    """

    explanation = "There are missing type annotations in the code."
    name = "func_pm_type_remove"
    conditions = [CodeProperty.IS_FUNCTION]

    def __init__(self, likelihood: float = DEFAULT_PM_LIKELIHOOD, seed: int = 24):
        super().__init__(likelihood=likelihood, seed=seed)

    def modify(self, code_entity):
        src = getattr(code_entity, "src", None)
        if not src:
            return None

        try:
            module = libcst.parse_module(src)
        except Exception:
            return None

        transformer = _TypeRemoveTransformer(self.flip)
        new_module = module.visit(transformer)

        if not transformer.modified:
            return None

        new_src = new_module.code
        return BugRewrite(
            rewrite=new_src,
            explanation=self.explanation,
            strategy=self.name,
        )