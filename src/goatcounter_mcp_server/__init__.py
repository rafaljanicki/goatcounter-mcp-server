from . import main

def main():
    """Main entry point for the package, returns a coroutine to be awaited by the caller."""
    return main.run()

# Optionally expose other important items at package level
__all__ = ['api_client', 'main']