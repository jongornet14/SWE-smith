import random
import libcst as cst
from swesmith.constants import BugRewrite, DEFAULT_PM_LIKELIHOOD


TYPE_MUTATIONS = ["str", "float", "bool"]
DICT_KEY_MUTATIONS = ["int", "bytes", "list"]


class TypeChangeModifier:
    """
    Introduces subtle type errors by mutating type annotations.
    """

    def __init__(self, likelihood=DEFAULT_PM_LIKELIHOOD, seed=42):
        self.rand = random.Random(seed)
        self.likelihood = likelihood

    def flip(self):
        return self.rand.random() < self.likelihood

    class Transformer(cst.CSTTransformer):
        def __init__(self, modifier):
            self.modifier = modifier

        def mutate_type(self, node):
            if not self.modifier.flip():
                return node

            # Handle Optional[T] -> T
            if isinstance(node, cst.Subscript) and isinstance(node.value, cst.Name):
                if node.value.value == "Optional":
                    return node.slice[0].slice.value

                if node.value.value == "List":
                    inner = node.slice[0].slice.value
                    new_type = self.modifier.rand.choice(TYPE_MUTATIONS)
                    return cst.Subscript(
                        value=node.value,
                        slice=[cst.SubscriptElement(slice=cst.Index(cst.Name(new_type)))]
                    )

                if node.value.value == "Dict":
                    key, val = node.slice
                    mutate_key = self.modifier.rand.choice([True, False])
                    if mutate_key:
                        new_key = self.modifier.rand.choice(DICT_KEY_MUTATIONS)
                        return cst.Subscript(
                            value=node.value,
                            slice=[
                                cst.SubscriptElement(slice=cst.Index(cst.Name(new_key))),
                                val
                            ]
                        )
                    else:
                        new_val = self.modifier.rand.choice(TYPE_MUTATIONS)
                        return cst.Subscript(
                            value=node.value,
                            slice=[
                                key,
                                cst.SubscriptElement(slice=cst.Index(cst.Name(new_val)))
                            ]
                        )

            # Primitive type mutation
            if isinstance(node, cst.Name):
                new_type = self.modifier.rand.choice(TYPE_MUTATIONS)
                return cst.Name(new_type)

            return node

        def leave_Annotation(self, original_node, updated_node):
            return updated_node.with_changes(
                annotation=self.mutate_type(updated_node.annotation)
            )

    def modify(self, code_entity):
        module = cst.parse_module(code_entity.src_code)
        transformer = self.Transformer(self)
        modified = module.visit(transformer)

        if modified.code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified.code,
            explanation="Introduced type mutation bug.",
            strategy="type_change"
        )


class TypeRemoveModifier:
    """
    Removes type annotations entirely.
    """

    def __init__(self, likelihood=DEFAULT_PM_LIKELIHOOD, seed=42):
        self.rand = random.Random(seed)
        self.likelihood = likelihood

    def flip(self):
        return self.rand.random() < self.likelihood

    class Transformer(cst.CSTTransformer):
        def __init__(self, modifier):
            self.modifier = modifier

        def leave_Annotation(self, original_node, updated_node):
            if self.modifier.flip():
                return None
            return updated_node

    def modify(self, code_entity):
        module = cst.parse_module(code_entity.src_code)
        transformer = self.Transformer(self)
        modified = module.visit(transformer)

        if modified.code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified.code,
            explanation="Removed type annotation from code.",
            strategy="type_remove"
        )