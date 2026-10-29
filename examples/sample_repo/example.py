def normalize_name(name: str) -> str:
    """Return a trimmed, lowercase name."""
    return name.strip().lower()


class ExampleService:
    def greet(self, name: str) -> str:
        return f"hello {normalize_name(name)}"
