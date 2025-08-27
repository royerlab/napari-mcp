# Security Policy

## 🚨 Critical Security Information

**napari-mcp includes tools that can execute arbitrary code and install packages.** This poses significant security risks if not used properly.

### High-Risk Components

| Tool | Risk Level | Description |
|------|------------|-------------|
| `execute_code()` | **🔴 CRITICAL** | Executes arbitrary Python code in the server environment |
| `install_packages()` | **🔴 CRITICAL** | Installs arbitrary Python packages via pip |
| All other tools | **🟡 LOW** | Read-only or napari-specific operations |

### Security Best Practices

#### ✅ **SAFE Usage**
- **Local development only** - Use on `localhost` connections
- **Trusted AI assistants** - Claude Desktop, local LLMs
- **Isolated environments** - Virtual environments, containers
- **Code review** - Always review generated code before execution
- **Monitoring** - Log all code execution requests

#### ❌ **DANGEROUS Usage**
- **Public networks** - Never expose to internet/untrusted networks
- **Production systems** - No production deployment without sandboxing
- **Shared systems** - Avoid on multi-user systems
- **Sensitive data** - Don't use with access to confidential information

### Recommended Deployment

```bash
# 1. Use isolated virtual environment
python -m venv napari-mcp-env
source napari-mcp-env/bin/activate

# 2. Install only in development environments
pip install napari-mcp

# 3. Run with local-only binding
napari-mcp --host 127.0.0.1
```

### Disable High-Risk Features

If you need to use napari-mcp in a more controlled environment, consider:

1. **Fork the repository** and remove `execute_code()` and `install_packages()` functions
2. **Use firewall rules** to restrict network access
3. **Container isolation** with restricted capabilities
4. **Monitor process execution** with tools like `strace` or `procmon`

## Vulnerability Reporting

### Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ |

### How to Report

**Do NOT create public GitHub issues for security vulnerabilities.**

Instead, please:

1. **Email**: Send details to [security-contact-email] (replace with actual contact)
2. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

3. **Response Time**: We aim to acknowledge reports within 48 hours

### Security Updates

- Security fixes will be released as patch versions
- Critical vulnerabilities will be addressed immediately
- Users will be notified via GitHub releases and README updates

## Risk Assessment Matrix

| Scenario | Risk Level | Recommendation |
|----------|------------|----------------|
| Local development with Claude Desktop | 🟢 **LOW** | ✅ Recommended usage |
| Local development with unknown AI | 🟡 **MEDIUM** | ⚠️ Review all code execution |
| Shared development machine | 🟠 **HIGH** | ❌ Use container isolation |
| Network-accessible deployment | 🔴 **CRITICAL** | ❌ Never do this |
| Production environment | 🔴 **CRITICAL** | ❌ Requires major security controls |

## Incident Response

If you discover that napari-mcp has been compromised or used maliciously:

1. **Immediately stop** the napari-mcp server
2. **Isolate** the affected system from the network
3. **Scan** for unauthorized code execution or installed packages
4. **Review logs** for suspicious activity
5. **Report** the incident following the vulnerability reporting process

## Security Checklist for Users

Before using napari-mcp, ensure:

- [ ] Running in isolated virtual environment
- [ ] No sensitive data accessible to the process
- [ ] Network access restricted to localhost only
- [ ] Monitoring logs for executed code
- [ ] Regular security updates applied
- [ ] Understanding of code execution implications

---

**Remember: With great power comes great responsibility. Use napari-mcp's code execution features wisely.**
