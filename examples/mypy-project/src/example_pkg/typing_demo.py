"""Demonstration of typing issues that mypy can detect."""  # noqa: CPY001


# Intentional: untyped function so mypy reports missing annotations; noqa keeps Ruff from blocking this demo
def greet(name):  # Missing type annotations - mypy will flag this  # noqa: ANN001, ANN201, D103
    return f"Hello, {name}!"


# Intentional: incorrect return annotation so mypy reports a type mismatch; noqa keeps Ruff from blocking this demo
def add_numbers(x: int, y: int) -> str:  # Return type mismatch  # noqa: D103, FURB118
    return x + y  # Returns int, not str


# Intentional: use of bare list so mypy reports missing generic type parameters; noqa keeps Ruff from blocking this demo
def process_data(items: list) -> int:  # Unspecified generic type  # noqa: D103
    return len(items)


# Intentional: class with incomplete typing so mypy reports missing annotations; noqa keeps Ruff from blocking this demo
class Calculator:  # noqa: D101
    # Intentional: constructor parameter left untyped so mypy reports missing annotations; noqa keeps Ruff from blocking this demo  # noqa: E501
    def __init__(self, initial_value):  # Missing type annotation  # noqa: ANN001, ANN204, D107
        self.value = initial_value

    # Intentional: method missing an explicit return annotation so mypy reports it; noqa keeps Ruff from blocking this demo  # noqa: E501
    def add(self, amount: int):  # Missing return type  # noqa: ANN201, D102
        self.value += amount
        return self.value


if __name__ == "__main__":
    # Intentional: runtime print examples so users can see outputs; T201 is suppressed so Ruff does not block this demo
    print(greet("World"))  # noqa: T201
    print(add_numbers(5, 3))  # noqa: T201
