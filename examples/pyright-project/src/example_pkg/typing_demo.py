"""Demonstration of typing issues that pyright can detect."""  # noqa: CPY001

from typing import Optional


# Intentional: potential None access so pyright reports missing guard; noqa keeps Ruff from blocking this demo
def process_optional(value: Optional[str]) -> int:  # noqa: D103, UP045
    # Pyright will flag potential None access
    return len(value)  # Should check if value is None first


# Intentional: parameter left as implicit Any so pyright reports it; noqa keeps Ruff from blocking this demo
def implicit_any(data):  # Parameter has implicit Any type  # noqa: ANN001, ANN201, D103
    return data.get("key")  # Unknown attribute access


# Intentional: union type without proper narrowing so pyright reports invalid attribute access; noqa keeps Ruff from blocking this demo  # noqa: E501
def type_narrowing_demo(value: str | int) -> str:  # noqa: D103
    # Pyright excels at type narrowing
    return value.upper()  # Error: 'int' has no attribute 'upper'


# Intentional: class uses overly general typing so pyright reports configuration shape issues; noqa keeps Ruff from blocking this demo  # noqa: E501
class DataProcessor:  # noqa: D101
    # Intentional: config annotated as plain dict so pyright reports overly general type; noqa keeps Ruff from blocking this demo  # noqa: E501
    def __init__(self, config: dict):  # dict is too general  # noqa: ANN204, D107
        self.config = config

    # Intentional: missing return annotation so pyright reports incomplete typing; noqa keeps Ruff from blocking this demo  # noqa: E501
    def get_setting(self, key: str):  # Missing return type  # noqa: ANN201, D102
        return self.config.get(key, "default")


# Intentional: match statement omits the None case so pyright reports incomplete pattern coverage; noqa keeps Ruff from blocking this demo  # noqa: E501
def incomplete_match(value: str | int | None) -> str:  # noqa: D103
    match value:
        case str():
            return value
        case int():
            return str(value)
        # Missing None case - pyright will flag incomplete pattern


if __name__ == "__main__":
    # Intentional: runtime print examples so users can see outputs; T201 is suppressed so Ruff does not block this demo
    print(process_optional("test"))  # noqa: T201
    print(implicit_any({"key": "value"}))  # noqa: T201
