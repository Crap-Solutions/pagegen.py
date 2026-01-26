#!/usr/bin/env python3.11
"""
Test for nested user folder support
"""

import sys
sys.path.insert(0, '/home/user/private/pagegen.py')

from generator import get_output_path
from pathlib import Path

content_root = Path('/content')
output_root = Path('/output')

# Test nested user folder
source = content_root / '~user/category/index.md'
result = get_output_path(source, content_root, output_root)
expected = output_root / '~user/category.html'

print(f"Source: {source}")
print(f"Result: {result}")
print(f"Expected: {expected}")
print(f"Match: {result == expected}")
