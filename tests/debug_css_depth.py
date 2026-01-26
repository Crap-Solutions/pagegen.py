#!/usr/bin/env python3.11
"""
Debug script to understand CSS depth calculation
"""

import sys
sys.path.insert(0, '/home/user/private/pagegen.py')

from generator import get_output_path, get_relative_css_depth
from pathlib import Path

# Test case: content/~user/category/index.md
content_root = Path('/content')
output_root = Path('/output')

source = content_root / '~user/category/index.md'
output_path = get_output_path(source, content_root, output_root)

print(f"Source: {source}")
print(f"Output: {output_path}")
print(f"Output relative to output root: {output_path.relative_to(output_root)}")
print(f"Output parent parts: {output_path.relative_to(output_root).parent.parts}")
print(f"CSS depth (len(parent.parts)): {len(output_path.relative_to(output_root).parent.parts)}")
print(f"Calculated CSS path: {get_relative_css_depth(source, content_root, output_root)}")
print(f"Expected CSS path: ../")
print()

# What we need:
# For output/~user/category.html, CSS is at output/
# Going from ~user/category/ to output/ = 2 levels up = ../../
# Current calculation gives len(['~user', 'category']) = 2 = ../../
# So why is test expecting ../ ?

# Oh! CSS might be in output/~user/ not output/ ?
