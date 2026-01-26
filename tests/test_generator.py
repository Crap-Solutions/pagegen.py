#!/usr/bin/env python3.11
"""
Unit tests for pagegen.py

NOTE: Install dependencies before running tests:
    pip install -r requirements-dev.txt
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from generator import (
    parse_frontmatter,
    get_output_path,
    get_home_link,
    get_relative_css_depth,
)


def test_parse_frontmatter_with_yaml():
    """Test parsing YAML frontmatter"""
    content = "---\ntitle: Test\n---\nBody"
    metadata, body = parse_frontmatter(content)
    assert metadata == {'title': 'Test'}
    assert body == 'Body'


def test_parse_frontmatter_without_yaml():
    """Test parsing without YAML frontmatter"""
    content = "# Just a heading\n\nSome content"
    metadata, body = parse_frontmatter(content)
    assert metadata == {}
    assert body == content


def test_parse_frontmatter_empty_yaml():
    """Test parsing with empty YAML frontmatter"""
    content = "---\n---\nBody text"
    metadata, body = parse_frontmatter(content)
    assert metadata == {}
    assert body == 'Body text'


def test_parse_frontmatter_invalid_yaml():
    """Test parsing with invalid YAML - should return empty metadata"""
    content = "---\ntitle: Test: invalid\n---\nBody"
    metadata, body = parse_frontmatter(content)
    assert metadata == {}
    assert body.startswith('Body')


def test_get_output_path_homepage():
    """Test output path for homepage"""
    content_root = Path('/content')
    output_root = Path('/output')
    
    source = content_root / 'index.md'
    result = get_output_path(source, content_root, output_root)
    
    assert result == output_root / 'index.html'


def test_get_output_path_user_index():
    """Test output path for user index page"""
    content_root = Path('/content')
    output_root = Path('/output')
    
    source = content_root / '~user/index.md'
    result = get_output_path(source, content_root, output_root)
    
    assert result == output_root / '~user/index.html'


def test_get_output_path_blog_post():
    """Test output path for blog post with date prefix"""
    content_root = Path('/content')
    output_root = Path('/output')
    
    source = content_root / '~user/2025-01-25-hello-world.md'
    result = get_output_path(source, content_root, output_root)
    
    assert result == output_root / '~user/hello-world.html'


def test_get_output_path_regular_page():
    """Test output path for regular page"""
    content_root = Path('/content')
    output_root = Path('/output')
    
    source = content_root / 'about.md'
    result = get_output_path(source, content_root, output_root)
    
    assert result == output_root / 'pages/about.html'


def test_get_output_path_nested_user_folder():
    """Test output path for nested user folder"""
    content_root = Path('/content')
    output_root = Path('/output')
    
    source = content_root / '~user/category/index.md'
    result = get_output_path(source, content_root, output_root)
    
    assert result == output_root / '~user/category.html'


def test_get_home_link_root():
    """Test home link at root"""
    output_path = Path('/output')
    output_root = Path('/output')
    
    result = get_home_link(output_path, output_root)
    assert result == ''


def test_get_home_link_subdirectory():
    """Test home link from subdirectory"""
    output_path = Path('/output/~user/page.html')
    output_root = Path('/output')
    
    result = get_home_link(output_path, output_root)
    assert result == '../'


def test_get_home_link_deep_subdirectory():
    """Test home link from nested subdirectory"""
    output_path = Path('/output/~user/category/page.html')
    output_root = Path('/output')
    
    result = get_home_link(output_path, output_root)
    assert result == '../../'


def test_get_relative_css_depth_root():
    """Test CSS relative depth at root"""
    content_root = Path('/content')
    output_root = Path('/output')
    
    source = content_root / 'index.md'
    result = get_relative_css_depth(source, content_root, output_root)
    
    assert result == ''


def test_get_relative_css_depth_one_level():
    """Test CSS relative depth one level deep"""
    content_root = Path('/content')
    output_root = Path('/output')
    
    source = content_root / '~user/index.md'
    result = get_relative_css_depth(source, content_root, output_root)
    
    assert result == '../'


def test_get_relative_css_depth_two_levels():
    """Test CSS relative depth for nested user folder"""
    content_root = Path('/content')
    output_root = Path('/output')

    # ~user/category/index.md outputs to ~user/category.html
    # Parent is ~user (1 part), so depth is 1 -> ../
    source = content_root / '~user/category/index.md'
    result = get_relative_css_depth(source, content_root, output_root)

    assert result == '../'


def test_date_sorting_mixed_types():
    """Test sorting works with mixed date types (str and datetime.date)"""
    from datetime import date

    posts = [
        {'metadata': {'date': date(2026, 1, 25)}},
        {'metadata': {'date': ''}},
        {'metadata': {'date': date(2026, 1, 20)}},
    ]

    sorted_posts = sorted(posts, key=lambda x: str(x['metadata'].get('date', '')), reverse=True)

    # When converted to strings and sorted descending:
    # '2026-01-25' > '2026-01-20' > ''
    assert sorted_posts[0]['metadata']['date'] == date(2026, 1, 25)
    assert sorted_posts[1]['metadata']['date'] == date(2026, 1, 20)
    assert sorted_posts[2]['metadata']['date'] == ''
