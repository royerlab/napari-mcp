# MkDocs Documentation Setup

This document explains the MkDocs documentation system for napari-mcp.

## 📖 Documentation Site

The documentation is built with [MkDocs](https://www.mkdocs.org/) using the [Material theme](https://squidfunk.github.io/mkdocs-material/).

**Live site:** https://royerlab.github.io/napari-mcp (deployed automatically)

## 🏗️ Structure

```
napari-mcp/
├── mkdocs.yml                    # Main configuration
├── docs/                         # Documentation source
│   ├── index.md                 # Homepage
│   ├── getting-started/         # Setup guides
│   ├── integrations/            # LLM integration guides  
│   ├── api/                     # API reference (auto-generated)
│   ├── guides/                  # User guides
│   ├── development/             # Developer docs
│   ├── scripts/                 # Build scripts
│   └── stylesheets/            # Custom CSS
├── requirements-docs.txt        # Documentation dependencies
└── .github/workflows/docs.yml  # Auto-deployment
```

## 🚀 Local Development

### Prerequisites

```bash
# Install documentation dependencies
pip install -r requirements-docs.txt

# Or with uv
uv pip install -r requirements-docs.txt
```

### Build and Serve

```bash
# Serve locally with auto-reload
mkdocs serve

# Build static site
mkdocs build

# Build and deploy to GitHub Pages
mkdocs gh-deploy
```

The local server runs at http://127.0.0.1:8000

## ⚙️ Features

### Automatic API Documentation

- **Auto-generated** from source code docstrings
- **NumPy-style** docstring support
- **Organized by category** (session, layers, utilities, etc.)
- **Live updates** when source code changes

### Material Theme Features

- **Dark/light mode** toggle
- **Search functionality** with highlighting
- **Mobile responsive** design
- **Social media previews** auto-generated
- **Code syntax highlighting** with copy buttons
- **Navigation tabs** and sections

### Content Organization

- **Getting Started** - Multiple setup methods
- **Integrations** - Claude Desktop, Cursor, etc.
- **API Reference** - Complete function documentation  
- **User Guides** - Workflows and best practices
- **Development** - Contributing and architecture

### Advanced Features

- **Custom CSS** styling for better appearance
- **Mermaid diagrams** support
- **Tabbed content** for different platforms
- **Admonitions** for tips, warnings, notes
- **Feedback system** for page improvements

## 🔄 Auto-Deployment

Documentation is automatically deployed via GitHub Actions:

- **Trigger:** Push to `main` branch with doc changes
- **Build:** MkDocs Material with all plugins
- **Deploy:** GitHub Pages at https://royerlab.github.io/napari-mcp
- **Preview:** PR comments show build status

## 📝 Writing Documentation

### File Locations

| Content Type | Location | Example |
|--------------|----------|---------|
| **Setup guides** | `docs/getting-started/` | quickstart.md |
| **Integration guides** | `docs/integrations/` | claude-desktop.md |
| **User tutorials** | `docs/guides/` | basic-usage.md |
| **API reference** | `docs/api/` | Auto-generated |
| **Developer docs** | `docs/development/` | contributing.md |

### Markdown Extensions

The site supports advanced Markdown features:

````markdown
# Syntax highlighting
```python
def example():
    pass
```

# Admonitions  
!!! tip "Pro Tip"
    This is helpful information

# Tabs
=== "Option 1"
    Content for option 1
    
=== "Option 2" 
    Content for option 2

# Tables with sorting
| Feature | Status |
|---------|--------|
| Search | ✅ Working |
````

### API Documentation

Function documentation is automatically extracted from docstrings:

```python
async def example_function(param: str) -> dict[str, Any]:
    """
    Brief description of the function.
    
    Parameters
    ----------
    param : str
        Description of the parameter.
        
    Returns
    -------
    dict
        Description of return value.
    """
```

## 🎨 Customization

### Styling

Custom CSS is in `docs/stylesheets/extra.css`:

- Card hover effects
- Improved table styling  
- Better mobile experience
- Custom badge styling

### Configuration

Main configuration in `mkdocs.yml`:

- **Theme settings** - Colors, features, icons
- **Plugin configuration** - Search, API docs, etc.
- **Navigation structure** - Page organization
- **Markdown extensions** - Syntax features

## 📊 Analytics and Feedback

- **Page feedback** system for user input
- **GitHub integration** for issue reporting
- **Social media** preview generation
- **Search analytics** via Material theme

## 🐛 Troubleshooting

### Common Issues

**Build failures:**
```bash
# Check for missing files referenced in nav
mkdocs build --strict

# Verbose output for debugging
mkdocs build --verbose
```

**Missing dependencies:**
```bash
pip install -r requirements-docs.txt
```

**Local server not updating:**
```bash
# Clear browser cache
# Restart mkdocs serve
```

### Performance

- **Build time:** ~1 second for full site
- **Incremental updates** during development
- **Optimized images** and assets
- **Minimal JavaScript** for fast loading

## 🚀 Deployment Status

Current deployment setup:

- ✅ **GitHub Actions** configured for auto-deployment
- ✅ **GitHub Pages** enabled for repository
- ✅ **Domain** configured (royerlab.github.io/napari-mcp)
- ✅ **SSL certificate** automatically provided
- ✅ **CDN delivery** via GitHub's infrastructure

## 📈 Future Enhancements

Planned improvements:

- **API examples** with interactive code snippets
- **Video tutorials** embedded in guides  
- **Changelog** integration with releases
- **Contributor profiles** and statistics
- **Multi-language** support if needed
- **Version selector** for different releases

---

**The documentation system is ready for professional use!** 🎉

Contributors can focus on writing content while the system handles:
- Automatic API documentation
- Professional styling and navigation  
- Mobile-friendly responsive design
- Search functionality
- GitHub Pages deployment