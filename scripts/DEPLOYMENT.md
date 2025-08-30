# Documentation Deployment Scripts

Scripts for deploying napari-mcp documentation to the HPC website.

## Available Scripts

### `deploy_docs.sh` - Basic Deployment

Simple script that builds and deploys documentation.

```bash
# Basic deployment
./scripts/deploy_docs.sh

# Test run without deploying
./scripts/deploy_docs.sh --dry-run
```

**Features:**
- ✅ Builds documentation with MkDocs
- ✅ Creates backup of existing deployment
- ✅ Copies to HPC website path
- ✅ Sets proper file permissions
- ✅ Basic error handling

### `deploy_docs_safe.sh` - Production Deployment

Advanced script with comprehensive safety checks and rollback capabilities.

```bash
# Safe deployment with confirmation prompts
./scripts/deploy_docs_safe.sh

# Dry run to see what would be deployed
./scripts/deploy_docs_safe.sh --dry-run

# Force deployment without prompts (for CI/automation)
./scripts/deploy_docs_safe.sh --force

# Show help
./scripts/deploy_docs_safe.sh --help
```

**Features:**
- ✅ All basic deployment features
- ✅ Git status checking
- ✅ Staging directory for safer deployment
- ✅ Comprehensive verification
- ✅ Automatic rollback on failure
- ✅ Detailed logging and progress indicators
- ✅ Safety prompts and confirmations

## Deployment Target

**Path:** `/hpc/websites/onsite.czbiohub.org/royerlab/napari-mcp`
**URL:** `https://onsite.czbiohub.org/royerlab/napari-mcp`

## Prerequisites

### System Requirements

1. **uv** - Python package manager
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Write access** to the HPC deployment path
   ```bash
   # Test write access
   touch /hpc/websites/onsite.czbiohub.org/royerlab/test && rm /hpc/websites/onsite.czbiohub.org/royerlab/test
   ```

3. **Documentation dependencies**
   ```bash
   # Automatically installed by scripts, or manually:
   uv pip install -r requirements-docs.txt
   ```

### File Structure

Before running deployment, ensure:
- You're in the `napari-mcp` root directory
- `mkdocs.yml` exists
- `docs/` directory contains all documentation
- `requirements-docs.txt` has all dependencies

## Deployment Process

Both scripts follow this process:

1. **Pre-checks** - Verify environment and permissions
2. **Dependencies** - Install/update documentation packages
3. **Build** - Generate static site with `mkdocs build --strict`
4. **Backup** - Create timestamped backup of existing site
5. **Deploy** - Copy new files to HPC path
6. **Verify** - Check deployment succeeded
7. **Cleanup** - Remove temporary files

## Safety Features

### Backups

Every deployment creates a timestamped backup:
```
/hpc/websites/onsite.czbiohub.org/royerlab/napari-mcp_backup_20250827_143022
```

### Rollback

If deployment fails, the safe script automatically attempts rollback to the backup.

### Verification

Scripts check for:
- Critical files exist (index.html, search files)
- Proper file permissions (644 for files, 755 for directories)
- Minimum file count threshold
- Build quality (strict mode)

## Usage Examples

### First Deployment

```bash
# Test first with dry run
./scripts/deploy_docs_safe.sh --dry-run

# Review the output, then deploy for real
./scripts/deploy_docs_safe.sh
```

### Regular Updates

```bash
# Quick deployment after docs changes
./scripts/deploy_docs.sh

# Or with safety checks
./scripts/deploy_docs_safe.sh --force
```

### CI/CD Integration

```bash
# Automated deployment (no prompts)
./scripts/deploy_docs_safe.sh --force
```

## Troubleshooting

### Permission Issues

```bash
# Check directory ownership
ls -la /hpc/websites/onsite.czbiohub.org/royerlab/

# Fix permissions if needed
sudo chown -R $(whoami) /hpc/websites/onsite.czbiohub.org/royerlab/napari-mcp
```

### Build Failures

```bash
# Test build locally
uv run mkdocs build --strict --verbose

# Check for missing files or broken links
uv run mkdocs build --strict 2>&1 | grep WARNING
```

### Network/Access Issues

```bash
# Test HPC connectivity
ssh your-hpc-server "ls -la /hpc/websites/onsite.czbiohub.org/royerlab/"

# Check if path is mounted correctly
df -h /hpc/websites/onsite.czbiohub.org/
```

## Rollback Procedure

If you need to manually rollback to a previous version:

```bash
# Find available backups
ls -la /hpc/websites/onsite.czbiohub.org/royerlab/napari-mcp_backup_*

# Rollback to specific backup
BACKUP_DIR="/hpc/websites/onsite.czbiohub.org/royerlab/napari-mcp_backup_20250827_143022"
rm -rf /hpc/websites/onsite.czbiohub.org/royerlab/napari-mcp/*
cp -r "$BACKUP_DIR"/* /hpc/websites/onsite.czbiohub.org/royerlab/napari-mcp/
```

## Monitoring

After deployment, verify the site works:

```bash
# Check if index page loads
curl -I https://onsite.czbiohub.org/royerlab/napari-mcp

# Check specific pages
curl -I https://onsite.czbiohub.org/royerlab/napari-mcp/getting-started/

# Monitor logs (if available)
tail -f /var/log/nginx/access.log | grep napari-mcp
```

---

**Ready to deploy?** Use `deploy_docs_safe.sh` for the most reliable deployment experience! 🚀
