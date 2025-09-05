#!/usr/bin/env python3
"""Analyze test performance and provide optimization recommendations."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_tests_with_profiling() -> dict[str, Any]:
    """Run tests and collect performance metrics."""
    print("Running tests with performance profiling...")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-m",
            "not realgui",
            "--durations=0",
            "--json-report",
            "--json-report-file=test-report.json",
            "-q",
        ],
        capture_output=True,
        text=True,
    )

    # Parse test report
    with open("test-report.json") as f:
        report = json.load(f)

    return report


def analyze_slow_tests(
    report: dict[str, Any], threshold: float = 1.0
) -> list[tuple[str, float]]:
    """Identify tests slower than threshold."""
    slow_tests = []

    for test in report.get("tests", []):
        duration = test.get("call", {}).get("duration", 0)
        if duration > threshold:
            slow_tests.append((test["nodeid"], duration))

    return sorted(slow_tests, key=lambda x: x[1], reverse=True)


def analyze_test_distribution(report: dict[str, Any]) -> dict[str, int]:
    """Analyze test distribution across files."""
    distribution = {}

    for test in report.get("tests", []):
        file_path = test["nodeid"].split("::")[0]
        distribution[file_path] = distribution.get(file_path, 0) + 1

    return distribution


def suggest_parallelization_strategy(report: dict[str, Any]) -> dict[str, Any]:
    """Suggest optimal parallelization strategy."""
    total_tests = len(report.get("tests", []))
    total_duration = report.get("duration", 0)

    suggestions = {
        "total_tests": total_tests,
        "total_duration": total_duration,
        "recommended_workers": min(4, total_tests // 10),
        "estimated_speedup": min(3.5, total_tests / 20),
    }

    # Analyze test dependencies
    test_files = set()
    for test in report.get("tests", []):
        test_files.add(test["nodeid"].split("::")[0])

    suggestions["test_files"] = len(test_files)
    suggestions["avg_tests_per_file"] = (
        total_tests / len(test_files) if test_files else 0
    )

    return suggestions


def generate_optimization_report(report: dict[str, Any]) -> None:
    """Generate comprehensive optimization report."""
    print("\n" + "=" * 60)
    print("TEST PERFORMANCE ANALYSIS REPORT")
    print("=" * 60)

    # Overall metrics
    print(f"\nTotal tests: {len(report.get('tests', []))}")
    print(f"Total duration: {report.get('duration', 0):.2f}s")
    print(f"Passed: {report.get('summary', {}).get('passed', 0)}")
    print(f"Failed: {report.get('summary', {}).get('failed', 0)}")

    # Slow tests
    slow_tests = analyze_slow_tests(report, threshold=1.0)
    if slow_tests:
        print("\n" + "-" * 40)
        print("SLOW TESTS (>1s):")
        for test, duration in slow_tests[:10]:
            print(f"  {duration:6.2f}s - {test}")

    # Test distribution
    distribution = analyze_test_distribution(report)
    print("\n" + "-" * 40)
    print("TEST DISTRIBUTION:")
    sorted_dist = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
    for file_path, count in sorted_dist[:5]:
        print(f"  {count:3d} tests - {file_path}")

    # Parallelization suggestions
    suggestions = suggest_parallelization_strategy(report)
    print("\n" + "-" * 40)
    print("PARALLELIZATION RECOMMENDATIONS:")
    print(f"  Recommended workers: {suggestions['recommended_workers']}")
    print(f"  Estimated speedup: {suggestions['estimated_speedup']:.1f}x")
    print(f"  Test files: {suggestions['test_files']}")
    print(f"  Avg tests/file: {suggestions['avg_tests_per_file']:.1f}")

    # Optimization recommendations
    print("\n" + "-" * 40)
    print("OPTIMIZATION RECOMMENDATIONS:")

    recommendations = []

    if suggestions["total_duration"] > 60:
        recommendations.append(
            "• Enable pytest-xdist with -n auto for parallel execution"
        )

    if len(slow_tests) > 5:
        recommendations.append(
            "• Mark slow tests with @pytest.mark.slow and run separately"
        )

    if suggestions["avg_tests_per_file"] > 20:
        recommendations.append(
            "• Consider splitting large test files for better parallelization"
        )

    if suggestions["test_files"] > 10:
        recommendations.append("• Use --dist loadscope for better test distribution")

    recommendations.append(
        "• Enable test result caching with --cache-clear on first run"
    )
    recommendations.append(
        "• Use coverage.py's parallel mode for accurate coverage with xdist"
    )

    for rec in recommendations:
        print(rec)

    print("\n" + "=" * 60)


def main():
    """Main entry point."""
    try:
        # Install required packages
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pytest-json-report"],
            capture_output=True,
        )

        report = run_tests_with_profiling()
        generate_optimization_report(report)

        # Clean up
        Path("test-report.json").unlink(missing_ok=True)

    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
