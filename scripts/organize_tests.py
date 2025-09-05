#!/usr/bin/env python3
"""Organize and categorize tests with appropriate markers."""

import ast
import sys
from pathlib import Path


class TestAnalyzer(ast.NodeVisitor):
    """Analyze test files and suggest appropriate markers."""

    def __init__(self):
        self.tests = []
        self.imports = set()
        self.class_name = None

    def visit_Import(self, node):
        """Visit import nodes."""
        for alias in node.names:
            self.imports.add(alias.name)

    def visit_ImportFrom(self, node):
        """Visit import from nodes."""
        if node.module:
            self.imports.add(node.module)

    def visit_ClassDef(self, node):
        """Visit class definition nodes."""
        if node.name.startswith("Test"):
            self.class_name = node.name
            self.generic_visit(node)
            self.class_name = None

    def visit_FunctionDef(self, node):
        """Visit function definition nodes."""
        if node.name.startswith("test_"):
            test_info = {
                "name": node.name,
                "class": self.class_name,
                "decorators": [],
                "has_fixture": False,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
            }

            # Check decorators
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Attribute):
                    if decorator.attr == "mark":
                        test_info["decorators"].append(decorator.attr)
                elif isinstance(decorator, ast.Call) and hasattr(
                    decorator.func, "attr"
                ):
                    test_info["decorators"].append(decorator.func.attr)

            # Check for fixture usage
            for arg in node.args.args:
                if arg.arg in ["qtbot", "real_viewer", "mock_viewer", "tmp_path"]:
                    test_info["has_fixture"] = True
                    break

            self.tests.append(test_info)


def categorize_test_file(file_path: Path) -> dict[str, set[str]]:
    """Categorize a test file and suggest markers."""
    with open(file_path) as f:
        tree = ast.parse(f.read())

    analyzer = TestAnalyzer()
    analyzer.visit(tree)

    categories = {
        "unit": set(),
        "integration": set(),
        "slow": set(),
        "smoke": set(),
        "realgui": set(),
    }

    file_name = file_path.stem

    for test in analyzer.tests:
        test_name = test["name"]
        full_name = f"{test['class']}::{test_name}" if test["class"] else test_name

        # Check if already marked as realgui
        if "realgui" in str(file_path) or "real" in file_name:
            categories["realgui"].add(full_name)
            continue

        # Categorize based on patterns
        if any(x in test_name for x in ["mock", "simple", "basic", "util"]):
            categories["unit"].add(full_name)
        elif (
            any(
                x in test_name for x in ["integration", "end_to_end", "e2e", "workflow"]
            )
            or any(x in test_name for x in ["external", "bridge", "server"])
            or test["is_async"]
            and test["has_fixture"]
        ):
            categories["integration"].add(full_name)
        else:
            categories["unit"].add(full_name)

        # Mark as slow if it has certain patterns
        if any(x in test_name for x in ["complex", "full", "complete", "heavy"]):
            categories["slow"].add(full_name)

        # Mark key tests as smoke tests
        if (
            any(x in test_name for x in ["init", "start", "basic", "simple"])
            and len(full_name) < 50
        ):
            categories["smoke"].add(full_name)

    # Handle imports to determine test type
    if "mock" in " ".join(analyzer.imports):
        # Heavy mocking suggests unit tests
        for test in analyzer.tests:
            full_name = (
                f"{test['class']}::{test['name']}" if test["class"] else test["name"]
            )
            if full_name not in categories["integration"]:
                categories["unit"].add(full_name)

    return categories


def generate_marker_suggestions(test_dir: Path) -> None:
    """Generate marker suggestions for all test files."""
    print("SUGGESTED TEST MARKERS")
    print("=" * 60)

    all_categories = {
        "unit": [],
        "integration": [],
        "slow": [],
        "smoke": [],
        "realgui": [],
    }

    test_files = sorted(test_dir.glob("test_*.py"))

    for test_file in test_files:
        categories = categorize_test_file(test_file)

        for category, tests in categories.items():
            for test in tests:
                all_categories[category].append(f"{test_file.stem}::{test}")

    # Print suggestions
    for category, tests in all_categories.items():
        if tests:
            print(f"\n@pytest.mark.{category}")
            print("-" * 40)
            for test in sorted(tests)[:10]:  # Show first 10
                print(f"  {test}")
            if len(tests) > 10:
                print(f"  ... and {len(tests) - 10} more")

    # Print statistics
    print("\n" + "=" * 60)
    print("STATISTICS")
    print("-" * 40)
    total = sum(len(tests) for tests in all_categories.values())
    for category, tests in all_categories.items():
        percentage = (len(tests) / total * 100) if total > 0 else 0
        print(f"{category:12s}: {len(tests):3d} tests ({percentage:5.1f}%)")

    # Print pytest commands
    print("\n" + "=" * 60)
    print("SUGGESTED PYTEST COMMANDS")
    print("-" * 40)
    print("# Run only unit tests (fast)")
    print("pytest -m unit -n auto")
    print("\n# Run smoke tests (very fast)")
    print("pytest -m smoke -x")
    print("\n# Run integration tests")
    print("pytest -m integration")
    print("\n# Run all except slow and GUI tests")
    print('pytest -m "not slow and not realgui" -n auto')
    print("\n# Run everything")
    print("pytest -n auto")


def main():
    """Main entry point."""
    test_dir = Path("tests")
    if not test_dir.exists():
        print("Error: tests directory not found", file=sys.stderr)
        sys.exit(1)

    generate_marker_suggestions(test_dir)


if __name__ == "__main__":
    main()
