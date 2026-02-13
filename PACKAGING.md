# PyPI Packaging Guide for Winterfox

This guide covers building, testing, and publishing the winterfox package to PyPI.

## Prerequisites

```bash
# Install build tools
uv add --dev build twine

# Or with pip
pip install build twine
```

## Package Structure Verification

Ensure all required files are present:

```
winterfox/
├── src/winterfox/           # Source code
│   ├── __init__.py          # Version and exports
│   ├── __main__.py          # CLI entry point
│   └── ...
├── tests/                   # Test suite
├── pyproject.toml           # Package metadata
├── README.md                # Package description
├── LICENSE                  # Apache 2.0
├── CHANGELOG.md             # Version history
└── MANIFEST.in              # Additional files to include
```

## Building the Package

### 1. Clean Previous Builds

```bash
# Remove old build artifacts
rm -rf dist/ build/ src/*.egg-info
```

### 2. Build Source and Wheel Distributions

```bash
# Using python -m build (recommended)
python -m build

# This creates:
# - dist/winterfox-0.1.0.tar.gz (source distribution)
# - dist/winterfox-0.1.0-py3-none-any.whl (wheel)
```

### 3. Verify Package Contents

```bash
# Check what's in the wheel
unzip -l dist/winterfox-0.1.0-py3-none-any.whl

# Check what's in the source distribution
tar -tzf dist/winterfox-0.1.0.tar.gz
```

Expected contents:
- All Python files from `src/winterfox/`
- README.md, LICENSE, CHANGELOG.md
- pyproject.toml
- Tests (in source distribution only)

## Testing the Package Locally

### 1. Install in Development Mode

```bash
# Install package in editable mode
uv pip install -e .

# Or with pip
pip install -e .
```

### 2. Test CLI Command

```bash
# Verify CLI works
winterfox --help

# Test basic commands
winterfox init "Test" --north-star "Test research"
cd test_project
winterfox status
```

### 3. Test as Library

```python
# test_import.py
import winterfox
from winterfox import KnowledgeGraph, Orchestrator

print(f"winterfox version: {winterfox.__version__}")
print("All imports successful!")
```

Run: `python test_import.py`

### 4. Install from Built Wheel

```bash
# Create fresh virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install from wheel
pip install dist/winterfox-0.1.0-py3-none-any.whl

# Test
winterfox --help
python -c "import winterfox; print(winterfox.__version__)"

# Clean up
deactivate
rm -rf test_env
```

## Publishing to Test PyPI (Recommended First)

Test PyPI lets you practice publishing without affecting the real PyPI.

### 1. Create Test PyPI Account

- Go to https://test.pypi.org/account/register/
- Verify your email
- Set up 2FA (required)

### 2. Create API Token

- Go to https://test.pypi.org/manage/account/token/
- Create new token with scope: "Entire account"
- Copy the token (starts with `pypi-`)

### 3. Configure Token

```bash
# Create/edit ~/.pypirc
cat > ~/.pypirc << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TEST-PYPI-TOKEN-HERE

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-YOUR-REAL-PYPI-TOKEN-HERE
EOF

# Secure the file
chmod 600 ~/.pypirc
```

### 4. Upload to Test PyPI

```bash
# Upload using twine
twine upload --repository testpypi dist/*

# You'll see:
# Uploading distributions to https://test.pypi.org/legacy/
# Uploading winterfox-0.1.0-py3-none-any.whl
# Uploading winterfox-0.1.0.tar.gz
```

### 5. Test Installation from Test PyPI

```bash
# Create fresh environment
python -m venv test_testpypi
source test_testpypi/bin/activate

# Install from Test PyPI (with dependencies from real PyPI)
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            winterfox

# Test
winterfox --help

# Clean up
deactivate
rm -rf test_testpypi
```

View your package: https://test.pypi.org/project/winterfox/

## Publishing to Real PyPI

**⚠️ IMPORTANT**: Once published to PyPI, you cannot:
- Delete or modify a release
- Re-upload the same version number

### 1. Create PyPI Account

- Go to https://pypi.org/account/register/
- Verify your email
- Set up 2FA (required)

### 2. Create API Token

- Go to https://pypi.org/manage/account/token/
- Create new token with scope: "Entire account" (or project-specific after first upload)
- Copy the token
- Add to `~/.pypirc` under `[pypi]` section

### 3. Final Pre-Upload Checks

```bash
# 1. All tests pass
uv run pytest tests/ -v
# Expected: 38/38 passing

# 2. Version is correct
grep "version =" pyproject.toml
# Should show: version = "0.1.0"

# 3. CHANGELOG is updated
grep "0.1.0" CHANGELOG.md
# Should show release notes

# 4. README looks good
head -20 README.md

# 5. Build is clean
rm -rf dist/ build/ src/*.egg-info
python -m build

# 6. Check with twine
twine check dist/*
# Should show: Checking dist/... PASSED
```

### 4. Upload to PyPI

```bash
# Upload to real PyPI
twine upload dist/*

# You'll see:
# Uploading distributions to https://upload.pypi.org/legacy/
# Uploading winterfox-0.1.0-py3-none-any.whl
# Uploading winterfox-0.1.0.tar.gz
# View at: https://pypi.org/project/winterfox/0.1.0/
```

### 5. Verify Installation

```bash
# Fresh environment
python -m venv verify_pypi
source verify_pypi/bin/activate

# Install from PyPI
pip install winterfox

# Test
winterfox --help
python -c "import winterfox; print(winterfox.__version__)"

# Clean up
deactivate
rm -rf verify_pypi
```

### 6. Create GitHub Release

```bash
# Tag the release
git tag -a v0.1.0 -m "Release v0.1.0 - First production release"
git push origin v0.1.0

# Create release on GitHub
# Go to: https://github.com/siinnche/winterfox/releases/new
# - Tag: v0.1.0
# - Title: "Winterfox v0.1.0 - Autonomous Research System"
# - Description: Copy from CHANGELOG.md
# - Attach: dist/winterfox-0.1.0.tar.gz and dist/winterfox-0.1.0-py3-none-any.whl
```

## Post-Publication

### Update Package Metadata

After first successful upload, create a project-specific API token:

1. Go to https://pypi.org/manage/project/winterfox/settings/
2. Create token with scope: "Project: winterfox"
3. Update `~/.pypirc` with new token

### Announce Release

Share on:
- GitHub Discussions
- Python Discord
- Reddit: r/Python, r/MachineLearning
- Twitter/X
- Hacker News (Show HN)

### Monitor Package

- PyPI page: https://pypi.org/project/winterfox/
- Download stats: https://pypistats.org/packages/winterfox
- Security advisories: https://pypi.org/project/winterfox/#security

## Releasing New Versions

### Version Numbering (Semantic Versioning)

- **Patch** (0.1.X): Bug fixes, documentation
- **Minor** (0.X.0): New features, backwards compatible
- **Major** (X.0.0): Breaking changes

### Release Workflow

```bash
# 1. Update version in pyproject.toml
# version = "0.1.1"

# 2. Update CHANGELOG.md
# Add [0.1.1] section with changes

# 3. Run tests
uv run pytest tests/ -v

# 4. Commit version bump
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to 0.1.1"

# 5. Build and upload
rm -rf dist/
python -m build
twine check dist/*
twine upload dist/*

# 6. Tag and push
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin main v0.1.1
```

## Troubleshooting

### "File already exists" Error

**Cause**: Trying to upload the same version twice.

**Solution**:
1. If testing: Use Test PyPI first
2. If real mistake: Bump version number (can't reuse)

### "Invalid or non-existent authentication"

**Cause**: Wrong API token or expired.

**Solution**:
1. Check token in `~/.pypirc`
2. Regenerate token on PyPI
3. Verify token starts with `pypi-`

### Package Missing Files

**Cause**: Files not included in MANIFEST.in or package discovery.

**Solution**:
```bash
# Check package contents
unzip -l dist/*.whl

# Update MANIFEST.in
# Add missing patterns

# Rebuild
rm -rf dist/ build/
python -m build
```

### Import Errors After Installation

**Cause**: Missing dependencies or incorrect package structure.

**Solution**:
```bash
# Check installed files
pip show -f winterfox

# Verify __init__.py exists
# Check dependencies in pyproject.toml
```

## Resources

- **Packaging Tutorial**: https://packaging.python.org/tutorials/packaging-projects/
- **PyPI Help**: https://pypi.org/help/
- **Twine Docs**: https://twine.readthedocs.io/
- **Build Docs**: https://build.pypa.io/

## Quick Reference

```bash
# Clean build
rm -rf dist/ build/ src/*.egg-info

# Build package
python -m build

# Check distribution
twine check dist/*

# Upload to Test PyPI
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*

# Test install
pip install winterfox

# Verify
winterfox --version
python -c "import winterfox; print(winterfox.__version__)"
```

---

**Ready to publish winterfox v0.1.0!** 🚀🦊
