# Changelog

All notable changes to napari-mcp will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release preparation
- Comprehensive GitHub repository setup
- Security documentation and warnings
- CI/CD workflows with GitHub Actions
- Pre-commit hooks configuration
- Contributing guidelines

### Security
- Added comprehensive security warnings for `execute_code()` and `install_packages()`
- Created SECURITY.md with vulnerability reporting guidelines
- Added security scanning to CI/CD pipeline

## [0.1.0] - 2024-08-27

### Added
- Initial napari MCP server implementation
- Core napari viewer control via MCP tools:
  - Session management (`init_viewer`, `close_viewer`, `session_information`)
  - Layer management (`add_image`, `add_labels`, `add_points`, `remove_layer`, etc.)
  - Viewer controls (`set_zoom`, `set_camera`, `reset_view`, etc.)
  - Screenshot functionality with base64 PNG export
  - Code execution capabilities (`execute_code`)
  - Package installation (`install_packages`)
- GUI management with non-blocking Qt event pump
- Comprehensive test suite with 96% coverage
- FastMCP integration for MCP protocol
- Support for Python 3.10-3.13
- Cross-platform compatibility (macOS, Linux, Windows)

### Dependencies
- fastmcp >=2.7.0
- napari >=0.5.5
- PyQt6 >=6.5.0
- qtpy >=2.4.1
- Pillow >=10.3.0
- imageio >=2.34.0
- numpy >=1.26.0

### Documentation
- README with quick start guide and API reference
- QUICKSTART.md for 5-minute setup
- Comprehensive tool documentation
- Claude Desktop integration examples
- Troubleshooting guide

### Testing
- Unit tests for all MCP tools
- Mock-based testing for CI environments
- Real GUI tests (optional, requires display)
- Edge case and error condition coverage
- Automated test execution with pytest

---

## Release Guidelines

### Version Numbering
- **Major (X.0.0)**: Breaking API changes, major security updates
- **Minor (0.X.0)**: New features, backward-compatible changes
- **Patch (0.0.X)**: Bug fixes, security patches

### Security Releases
- Security vulnerabilities will trigger immediate patch releases
- Security releases will be clearly marked in changelog
- Users will be notified via GitHub releases and README updates

### Breaking Changes
- Breaking changes will be clearly documented
- Migration guides will be provided for major version updates
- Deprecation warnings will be added before breaking changes when possible

---

## Contributing to Changelog

When contributing, please:
1. Add entries under `[Unreleased]` section
2. Use the categories: Added, Changed, Deprecated, Removed, Fixed, Security
3. Include brief descriptions with relevant issue/PR numbers
4. Follow the existing format and style
5. Security-related changes should be prominently documented
