import libcst

from swesmith.bug_gen.procedural.python.base import PythonProceduralModifier
from swesmith.constants import CodeProperty


# Type mapping for primitive type changes
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


class TypeChangeModifier(PythonProceduralModifier):
    """Modifies type annotations to introduce type-related bugs."""
    
    explanation: str = "The type annotations in the code are likely incorrect."
    name: str = "func_pm_type_change"
    conditions: list = [CodeProperty.IS_FUNCTION]
    min_complexity: int = 3

    class Transformer(PythonProceduralModifier.Transformer):
        def __init__(self, parent):
            super().__init__(parent)
            # Track whether we've modified anything yet
            self.modified = False
        
        def leave_Param(
            self, original_node: libcst.Param, updated_node: libcst.Param
        ) -> libcst.Param:
            """Modify parameter type annotations."""
            # Skip if we've already modified something
            if self.modified:
                return updated_node
            
            if updated_node.annotation is None:
                return updated_node
            
            # Use flip() to decide whether to try modifying this annotation
            if not self.flip():
                return updated_node
            
            # Get the annotation
            annotation = updated_node.annotation.annotation
            new_annotation = self._mutate_annotation(annotation)
            
            if new_annotation is None:
                return updated_node
            
            # Mark that we've modified something
            self.modified = True
            
            return updated_node.with_changes(
                annotation=libcst.Annotation(annotation=new_annotation)
            )
        
        def leave_FunctionDef(
            self, original_node: libcst.FunctionDef, updated_node: libcst.FunctionDef
        ) -> libcst.FunctionDef:
            """Modify return type annotations."""
            # Skip if we've already modified something
            if self.modified:
                return updated_node
            
            if updated_node.returns is None:
                return updated_node
            
            # Use flip() to decide whether to try modifying this annotation
            if not self.flip():
                return updated_node
            
            new_annotation = self._mutate_annotation(updated_node.returns.annotation)
            
            if new_annotation is None:
                return updated_node
            
            # Mark that we've modified something
            self.modified = True
            
            return updated_node.with_changes(
                returns=libcst.Annotation(annotation=new_annotation)
            )
        
        def leave_AnnAssign(
            self, original_node: libcst.AnnAssign, updated_node: libcst.AnnAssign
        ) -> libcst.AnnAssign:
            """Modify variable type annotations."""
            # Skip if we've already modified something
            if self.modified:
                return updated_node
            
            if updated_node.annotation is None:
                return updated_node
            
            # Use flip() to decide whether to try modifying this annotation
            if not self.flip():
                return updated_node
            
            new_annotation = self._mutate_annotation(updated_node.annotation.annotation)
            
            if new_annotation is None:
                return updated_node
            
            # Mark that we've modified something
            self.modified = True
            
            return updated_node.with_changes(
                annotation=libcst.Annotation(annotation=new_annotation)
            )
        
        def _mutate_annotation(self, annotation):
            """Mutate a type annotation to introduce a bug."""
            if isinstance(annotation, libcst.Name):
                # Simple type like int, str, bool
                type_name = annotation.value
                if type_name in PRIMITIVE_TYPE_SWAPS:
                    new_type = self.parent.rand.choice(PRIMITIVE_TYPE_SWAPS[type_name])
                    return libcst.Name(value=new_type)
            
            elif isinstance(annotation, libcst.Subscript):
                # Generic type like List[int], Dict[str, int], Optional[str]
                if isinstance(annotation.value, libcst.Name):
                    base_type = annotation.value.value
                    
                    # Handle Optional/Union by removing them
                    if base_type in ["Optional", "Union"]:
                        # Remove the Optional/Union wrapper
                        if isinstance(annotation.slice, list) and len(annotation.slice) > 0:
                            slice_item = annotation.slice[0]
                            if isinstance(slice_item, libcst.SubscriptElement):
                                return slice_item.slice.value
                        elif isinstance(annotation.slice, libcst.SubscriptElement):
                            return annotation.slice.slice.value
                    
                    # Change the generic type parameter
                    elif base_type in ["List", "Set", "Tuple"]:
                        # Try to change the inner type
                        if isinstance(annotation.slice, list) and len(annotation.slice) > 0:
                            slice_item = annotation.slice[0]
                            if isinstance(slice_item, libcst.SubscriptElement):
                                inner_type = slice_item.slice.value
                                new_inner = self._mutate_annotation(inner_type)
                                if new_inner:
                                    return annotation.with_changes(
                                        slice=[
                                            libcst.SubscriptElement(
                                                slice=libcst.Index(value=new_inner)
                                            )
                                        ]
                                    )
                    
                    # Change Dict key or value types
                    elif base_type == "Dict":
                        # Handle Dict[K, V] which uses a single SubscriptElement with Index slice
                        if isinstance(annotation.slice, list) and len(annotation.slice) == 1:
                            slice_elem = annotation.slice[0]
                            if isinstance(slice_elem, libcst.SubscriptElement) and isinstance(slice_elem.slice, libcst.Index):
                                index_val = slice_elem.slice.value
                                # The Index contains a Tuple with two elements
                                if isinstance(index_val, libcst.Tuple) and len(index_val.elements) == 2:
                                    key_elem = index_val.elements[0]
                                    val_elem = index_val.elements[1]
                                    
                                    # Randomly change key or value type
                                    if self.parent.rand.choice([True, False]):
                                        # Change key type
                                        new_key = self._mutate_annotation(key_elem.value)
                                        if new_key:
                                            return annotation.with_changes(
                                                slice=[
                                                    libcst.SubscriptElement(
                                                        slice=libcst.Index(
                                                            value=libcst.Tuple(
                                                                elements=[
                                                                    libcst.Element(value=new_key),
                                                                    val_elem,
                                                                ]
                                                            )
                                                        )
                                                    )
                                                ]
                                            )
                                    else:
                                        # Change value type
                                        new_val = self._mutate_annotation(val_elem.value)
                                        if new_val:
                                            return annotation.with_changes(
                                                slice=[
                                                    libcst.SubscriptElement(
                                                        slice=libcst.Index(
                                                            value=libcst.Tuple(
                                                                elements=[
                                                                    key_elem,
                                                                    libcst.Element(value=new_val),
                                                                ]
                                                            )
                                                        )
                                                    )
                                                ]
                                            )
            
            return None


class TypeRemoveModifier(PythonProceduralModifier):
    """Removes type annotations entirely."""
    
    explanation: str = "There are missing type annotations in the code."
    name: str = "func_pm_type_remove"
    conditions: list = [CodeProperty.IS_FUNCTION]
    min_complexity: int = 3

    class Transformer(PythonProceduralModifier.Transformer):
        def __init__(self, parent):
            super().__init__(parent)
            # Track whether we've removed anything yet
            self.modified = False
        
        def leave_FunctionDef(
            self, original_node: libcst.FunctionDef, updated_node: libcst.FunctionDef
        ) -> libcst.FunctionDef:
            """Remove return type annotations."""
            # Skip if we've already removed something
            if self.modified:
                return updated_node
            
            # Use flip() to decide whether to try removing this annotation
            if not self.flip():
                return updated_node
            
            if updated_node.returns is not None:
                self.modified = True
                return updated_node.with_changes(returns=None)
            
            return updated_node
        
        def leave_Param(
            self, original_node: libcst.Param, updated_node: libcst.Param
        ) -> libcst.Param:
            """Remove parameter type annotations."""
            # Skip if we've already removed something
            if self.modified:
                return updated_node
            
            # Use flip() to decide whether to try removing this annotation
            if not self.flip():
                return updated_node
            
            if updated_node.annotation is not None:
                self.modified = True
                return updated_node.with_changes(annotation=None)
            
            return updated_node
        
        def leave_AnnAssign(
            self, original_node: libcst.AnnAssign, updated_node: libcst.AnnAssign
        ) -> libcst.AnnAssign | libcst.Assign:
            """Convert annotated assignment to regular assignment."""
            # Skip if we've already removed something
            if self.modified:
                return updated_node
            
            # Use flip() to decide whether to try removing this annotation
            if not self.flip():
                return updated_node
            
            # Convert from annotated assignment to regular assignment
            if updated_node.value is not None:
                self.modified = True
                return libcst.Assign(
                    targets=[libcst.AssignTarget(target=updated_node.target)],
                    value=updated_node.value,
                )
            
            # If there's no value, we can't convert it, so leave it
            return updated_node
