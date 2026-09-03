# NAV Development & Testing Guide

## 1. Running Tests

```powershell
# Run entire test suite
python -m pytest tests/ -v

# Run only research capability tests
python -m pytest tests/test_research.py -v
2. Quality Checks
PowerShell

# Format code
python -m ruff format .

# Check linting
python -m ruff check .

# Check types
python -m mypy .
3. Running Demos
PowerShell

# S6 Persistent Memory Demo
python demo_s6.py

# S7 Systematic Research Demo
python demo_s7.py
