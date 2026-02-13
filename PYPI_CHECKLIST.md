# PyPI Publication Checklist

Use this checklist when publishing winterfox to PyPI.

## Pre-Publication Checks

### 1. Code Quality ✅

- [ ] All tests pass: `uv run pytest tests/ -v`
  - Expected: 38/38 passing
- [ ] No linting errors: `uv run ruff check src/`
- [ ] Type checking passes: `uv run mypy src/winterfox`
- [ ] Code formatted: `uv run ruff format src/`

### 2. Version & Documentation

- [ ] Version updated in `pyproject.toml`
- [ ] CHANGELOG.md updated with release notes
- [ ] README.md is current
- [ ] All example configs work
- [ ] Documentation links are valid

### 3. Package Structure

- [ ] `src/winterfox/__init__.py` exports correct version
- [ ] LICENSE file present (Apache 2.0)
- [ ] MANIFEST.in includes all necessary files
- [ ] No sensitive data in files (API keys, passwords)

### 4. Git Status

- [ ] All changes committed
- [ ] Working directory clean: `git status`
- [ ] Pushed to GitHub: `git push origin main`

## Building the Package

```bash
# 1. Clean previous builds
rm -rf dist/ build/ src/*.egg-info

# 2. Build distributions
python -m build

# 3. Verify files created
ls -lh dist/
# Should see:
# - winterfox-X.Y.Z.tar.gz (source)
# - winterfox-X.Y.Z-py3-none-any.whl (wheel)
```

## Verification

### 1. Check Package Contents

```bash
# Check wheel contents
unzip -l dist/winterfox-*.whl | head -20

# Check source distribution
tar -tzf dist/winterfox-*.tar.gz | head -20

# Verify includes:
# - All Python files from src/winterfox/
# - README.md, LICENSE, CHANGELOG.md
# - pyproject.toml
```

### 2. Validate with Twine

```bash
twine check dist/*

# Should output:
# Checking dist/winterfox-X.Y.Z.tar.gz: PASSED
# Checking dist/winterfox-X.Y.Z-py3-none-any.whl: PASSED
```

### 3. Test Installation Locally

```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

# Install from wheel
pip install dist/winterfox-*.whl

# Test CLI
winterfox --version
winterfox --help

# Test import
python -c "import winterfox; print(winterfox.__version__)"

# Clean up
deactivate
rm -rf test_env
```

## Publishing to Test PyPI (First Time)

### 1. Setup Test PyPI Account

- [ ] Created account at https://test.pypi.org/account/register/
- [ ] Email verified
- [ ] 2FA enabled
- [ ] API token created

### 2. Configure Credentials

```bash
# Create ~/.pypirc if not exists
cat > ~/.pypirc << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TEST-TOKEN-HERE
EOF

chmod 600 ~/.pypirc
```

### 3. Upload to Test PyPI

```bash
twine upload --repository testpypi dist/*

# Check at: https://test.pypi.org/project/winterfox/
```

### 4. Test Installation from Test PyPI

```bash
# Fresh environment
python -m venv test_testpypi
source test_testpypi/bin/activate

# Install from Test PyPI
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            winterfox

# Test
winterfox --version

# Clean up
deactivate
rm -rf test_testpypi
```

## Publishing to Real PyPI

### ⚠️ Final Checks (Point of No Return)

- [ ] **All tests pass**: 38/38
- [ ] **Version is correct**: Check `pyproject.toml`
- [ ] **CHANGELOG is complete**: Release notes written
- [ ] **Documentation is current**: README, guides up to date
- [ ] **Test PyPI worked**: Installed and tested successfully
- [ ] **Ready to commit**: This version can never be changed

### 1. Setup PyPI Account

- [ ] Created account at https://pypi.org/account/register/
- [ ] Email verified
- [ ] 2FA enabled
- [ ] API token created

### 2. Update Credentials

```bash
# Add to ~/.pypirc
[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-YOUR-REAL-TOKEN-HERE
```

### 3. Upload to PyPI

```bash
# Final check
twine check dist/*

# Upload (cannot be undone!)
twine upload dist/*

# Verify at: https://pypi.org/project/winterfox/
```

### 4. Test Installation from PyPI

```bash
# Fresh environment
python -m venv verify_pypi
source verify_pypi/bin/activate

# Install from PyPI
pip install winterfox

# Test
winterfox --version
python -c "import winterfox; print(winterfox.__version__)"

# Clean up
deactivate
rm -rf verify_pypi
```

## Post-Publication

### 1. Git Tag & Release

```bash
# Tag the version
VERSION=$(grep "version =" pyproject.toml | cut -d'"' -f2)
git tag -a v$VERSION -m "Release v$VERSION"
git push origin v$VERSION
```

### 2. Create GitHub Release

Go to: https://github.com/siinnche/winterfox/releases/new

- [ ] Tag: `v0.1.0`
- [ ] Title: `Winterfox v0.1.0 - Autonomous Research System`
- [ ] Description: Copy from CHANGELOG.md
- [ ] Attach files:
  - [ ] `dist/winterfox-0.1.0.tar.gz`
  - [ ] `dist/winterfox-0.1.0-py3-none-any.whl`
- [ ] Mark as latest release

### 3. Update Project Metadata

After first successful upload, create project-specific token:

1. Go to: https://pypi.org/manage/project/winterfox/settings/
2. Create token with scope: "Project: winterfox"
3. Update `~/.pypirc` with new token

### 4. Announce Release

- [ ] GitHub Discussions post
- [ ] Twitter/X announcement
- [ ] Reddit: r/Python
- [ ] Hacker News (Show HN)
- [ ] Dev.to article (optional)

## Monitoring

### Package Health

- [ ] PyPI page: https://pypi.org/project/winterfox/
- [ ] Download stats: https://pypistats.org/packages/winterfox
- [ ] Issues: https://github.com/siinnche/winterfox/issues
- [ ] Security: https://pypi.org/project/winterfox/#security

### Next Release Planning

- [ ] Increment version in `pyproject.toml`
- [ ] Create CHANGELOG section for next version
- [ ] Document new features in README
- [ ] Update examples if API changed

## Troubleshooting

### Build Fails

```bash
# Check for syntax errors
python -m py_compile src/winterfox/*.py

# Reinstall build tools
pip install --upgrade build twine
```

### Upload Fails: "File already exists"

**Cannot reuse version numbers!**

Solution:
1. Increment version in `pyproject.toml`
2. Update CHANGELOG.md
3. Rebuild: `rm -rf dist/ && python -m build`
4. Upload again

### Upload Fails: "Invalid authentication"

Check:
1. Token in `~/.pypirc` is correct
2. Token starts with `pypi-`
3. Token hasn't expired
4. Regenerate token if needed

### Import Errors After Install

Check:
1. `pip show winterfox` - verify files installed
2. `__init__.py` exports are correct
3. Dependencies in `pyproject.toml` are complete

## Quick Commands Reference

```bash
# Build
rm -rf dist/ build/ src/*.egg-info && python -m build

# Check
twine check dist/*

# Test PyPI
twine upload --repository testpypi dist/*

# Real PyPI
twine upload dist/*

# Test install
pip install winterfox

# Verify
winterfox --version
```

---

**Version**: 0.1.0
**Last Updated**: 2026-02-13

Use this checklist for every release! ✅
