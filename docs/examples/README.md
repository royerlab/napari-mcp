# Python Integration Examples

Working examples demonstrating how to use napari MCP server in custom Python scripts for workflow automation.

## 📁 Available Examples

### 1. OpenAI Integration (`openai_integration.py`)

**Description:** Use OpenAI GPT-4 with napari MCP server for AI-controlled image analysis.

**Use case:** Automated workflows where GPT-4 decides which napari operations to perform.

**Run:**
```bash
# Set your API key
export OPENAI_API_KEY="your-key-here"

# Run with installed packages
python openai_integration.py

# Or with uv (zero-install)
uv run --with openai --with mcp python openai_integration.py
```

**What it does:**
- Connects OpenAI GPT-4 to napari MCP server
- Lists available napari tools
- Uses GPT-4 to generate code for creating test images
- Executes the code in napari environment

---

### 2. Anthropic Claude Integration (`anthropic_integration.py`)

**Description:** Use Anthropic Claude with napari MCP server for intelligent microscopy analysis.

**Use case:** Automated workflows with Claude's advanced reasoning capabilities.

**Run:**
```bash
# Set your API key
export ANTHROPIC_API_KEY="your-key-here"

# Run with installed packages
python anthropic_integration.py

# Or with uv (zero-install)
uv run --with anthropic --with mcp python anthropic_integration.py
```

**What it does:**
- Connects Claude 3.5 Sonnet to napari MCP server
- Converts napari tools to Claude format
- Asks Claude to take a screenshot
- Executes napari tools based on Claude's decisions

---

### 3. Direct MCP Client (`direct_mcp_client.py`)

**Description:** Direct napari MCP automation without external LLMs.

**Use case:** Scripted workflows, batch processing, automated testing.

**Run:**
```bash
# No API key needed!
python direct_mcp_client.py

# Or with uv
uv run --with mcp python direct_mcp_client.py
```

**What it does:**
- Creates synthetic test data in napari
- Lists all layers
- Takes a screenshot
- Gets session information
- All without any external AI - pure automation

---

## 🎯 Use Cases

### Automated Image Processing Pipelines

Use these examples to build:
- **Batch processing** - Process hundreds of images automatically
- **Quality control** - Automated checks with AI assistance
- **Data augmentation** - Generate training data with napari
- **Reporting** - Automated analysis reports with screenshots

### Research Workflows

Apply to:
- **Reproducible analysis** - Script entire analysis pipelines
- **Multi-modal AI** - Combine vision models with napari control
- **Interactive notebooks** - Jupyter integration with AI assistance
- **Custom tools** - Build specialized analysis applications

### Integration Projects

Embed into:
- **Web applications** - Flask/FastAPI backends with napari
- **Desktop applications** - Qt apps with napari + AI
- **Cloud pipelines** - Serverless image processing
- **CI/CD workflows** - Automated testing with napari

---

## 🚀 Getting Started

1. **Choose your example** based on your use case
2. **Install dependencies:**
   ```bash
   pip install napari-mcp openai anthropic mcp
   ```
3. **Set API keys** (for OpenAI/Anthropic examples)
4. **Run the script** and modify for your needs

## 📚 Documentation

- **[Python Integration Guide](../integrations/python.md)** - Detailed explanation and advanced patterns
- **[API Reference](../api/index.md)** - All available napari MCP tools
- **[Troubleshooting](../guides/troubleshooting.md)** - Common issues

---

**These examples are starting points - customize them for your specific workflows!** 🔬✨