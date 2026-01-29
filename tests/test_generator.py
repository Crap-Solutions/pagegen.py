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
    render_markdown,
    get_current_year,
    generate_sitemap,
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


# ============================================================================
# Additional parse_frontmatter tests
# ============================================================================

def test_parse_frontmatter_multiple_fields():
    """Test parsing YAML with multiple fields"""
    from datetime import date
    content = "---\ntitle: Test Title\ndate: 2025-01-25\nauthor: John\n---\nBody content"
    metadata, body = parse_frontmatter(content)
    assert metadata == {
        'title': 'Test Title',
        'date': date(2025, 1, 25),  # YAML auto-converts dates
        'author': 'John'
    }
    assert body == 'Body content'


def test_parse_frontmatter_with_list():
    """Test parsing YAML with list values"""
    content = "---\ntags:\n  - python\n  - testing\n---\nContent"
    metadata, body = parse_frontmatter(content)
    assert metadata == {'tags': ['python', 'testing']}
    assert body == 'Content'


def test_parse_frontmatter_body_preserves_formatting():
    """Test that body content preserves its formatting"""
    content = "---\ntitle: Test\n---\n\n# Heading\n\nParagraph with **bold** text."
    metadata, body = parse_frontmatter(content)
    assert metadata == {'title': 'Test'}
    assert body == '# Heading\n\nParagraph with **bold** text.'


def test_parse_frontmatter_no_closing_delimiter():
    """Test content with opening but no closing delimiter"""
    content = "---\ntitle: Test\nBody content without closing delimiter"
    metadata, body = parse_frontmatter(content)
    assert metadata == {}
    assert body == content


# ============================================================================
# render_markdown tests
# ============================================================================

def test_render_markdown_basic():
    """Test basic markdown to HTML conversion"""
    md = "# Heading\n\nParagraph with **bold** and *italic*."
    html = render_markdown(md)
    assert '<h1>Heading</h1>' in html
    assert '<strong>bold</strong>' in html
    assert '<em>italic</em>' in html


def test_render_markdown_with_code_block():
    """Test markdown with fenced code block"""
    md = "```python\nprint('hello')\n```"
    html = render_markdown(md)
    assert '<code>' in html or '<pre>' in html


def test_render_markdown_with_table():
    """Test markdown with table"""
    md = "| A | B |\n|---|---|\n| 1 | 2 |"
    html = render_markdown(md)
    assert '<table>' in html


def test_render_markdown_strip_first_heading_h1():
    """Test stripping first h1 heading"""
    md = "# Title\n\nSome content"
    html = render_markdown(md, strip_first_heading=True)
    assert '<h1>' not in html
    assert 'Some content' in html


def test_render_markdown_strip_first_heading_h2():
    """Test stripping first h2 heading"""
    md = "## Title\n\nSome content"
    html = render_markdown(md, strip_first_heading=True)
    assert '<h2>' not in html
    assert 'Some content' in html


def test_render_markdown_no_strip():
    """Test markdown without stripping heading"""
    md = "# Title\n\nSome content"
    html = render_markdown(md, strip_first_heading=False)
    assert '<h1>Title</h1>' in html
    assert 'Some content' in html


# ============================================================================
# get_current_year tests
# ============================================================================

def test_get_current_year_default_format():
    """Test getting current year with default format"""
    from datetime import datetime
    expected_year = datetime.now().year
    result = get_current_year()
    assert result == str(expected_year)


def test_get_current_year_custom_format():
    """Test getting current date with custom format"""
    from datetime import datetime
    result = get_current_year('%Y-%m-%d')
    expected = datetime.now().strftime('%Y-%m-%d')
    assert result == expected


# ============================================================================
# Additional get_output_path tests
# ============================================================================

def test_get_output_path_blog_post_underscore_date():
    """Test blog post with underscore date format (YYYY_M_D-)"""
    content_root = Path('/content')
    output_root = Path('/output')

    source = content_root / '~user/2025_1_25-hello-world.md'
    result = get_output_path(source, content_root, output_root)

    assert result == output_root / '~user/hello-world.html'


def test_get_output_path_blog_post_no_date_prefix():
    """Test blog post without date prefix keeps full filename"""
    content_root = Path('/content')
    output_root = Path('/output')

    source = content_root / '~user/my-post.md'
    result = get_output_path(source, content_root, output_root)

    assert result == output_root / '~user/my-post.html'


def test_get_output_path_deep_nested_user_folder():
    """Test deeply nested user folder (e.g., ~user/category/subcategory/index.md)"""
    content_root = Path('/content')
    output_root = Path('/output')

    # For nested folders, it uses the immediate parent as filename
    source = content_root / '~user/category/subcategory/index.md'
    result = get_output_path(source, content_root, output_root)

    assert result == output_root / '~user/subcategory.html'


# ============================================================================
# generate_sitemap tests
# ============================================================================

def test_generate_sitemap_creates_file(tmp_path):
    """Test that sitemap.xml file is created"""
    from pathlib import Path
    import tempfile
    
    content_root = Path(tmp_path) / 'content'
    output_root = Path(tmp_path) / 'output'
    content_root.mkdir()
    output_root.mkdir()
    
    config = {
        'site': {
            'url': 'https://example.com'
        }
    }
    
    # Mock data
    pages = []
    blog_posts_by_user = {}
    users = []
    
    generate_sitemap(output_root, content_root, config, pages, blog_posts_by_user, users)
    
    sitemap_file = output_root / 'sitemap.xml'
    assert sitemap_file.exists()
    assert sitemap_file.is_file()


def test_generate_sitemap_contains_homepage(tmp_path):
    """Test that homepage is included with highest priority"""
    from pathlib import Path
    
    content_root = Path(tmp_path) / 'content'
    output_root = Path(tmp_path) / 'output'
    content_root.mkdir()
    output_root.mkdir()
    
    config = {
        'site': {
            'url': 'https://example.com'
        }
    }
    
    generate_sitemap(output_root, content_root, config, [], {}, [])
    
    sitemap_content = (output_root / 'sitemap.xml').read_text()
    assert '<loc>https://example.com/</loc>' in sitemap_content
    assert '<priority>1.0</priority>' in sitemap_content
    assert '<changefreq>daily</changefreq>' in sitemap_content


def test_generate_sitemap_contains_users(tmp_path):
    """Test that user index pages are included"""
    from pathlib import Path
    
    content_root = Path(tmp_path) / 'content'
    output_root = Path(tmp_path) / 'output'
    content_root.mkdir()
    output_root.mkdir()
    
    config = {
        'site': {
            'url': 'https://example.com'
        }
    }
    
    users = [
        {'name': '~user1'},
        {'name': '~user2'}
    ]
    
    generate_sitemap(output_root, content_root, config, [], {}, users)
    
    sitemap_content = (output_root / 'sitemap.xml').read_text()
    assert '<loc>https://example.com/~user1/index.html</loc>' in sitemap_content
    assert '<loc>https://example.com/~user2/index.html</loc>' in sitemap_content
    assert '<priority>0.7</priority>' in sitemap_content


def test_generate_sitemap_valid_xml_structure(tmp_path):
    """Test that generated sitemap has valid XML structure"""
    from pathlib import Path
    
    content_root = Path(tmp_path) / 'content'
    output_root = Path(tmp_path) / 'output'
    content_root.mkdir()
    output_root.mkdir()
    
    config = {
        'site': {
            'url': 'https://example.com'
        }
    }
    
    generate_sitemap(output_root, content_root, config, [], {}, [])
    
    sitemap_content = (output_root / 'sitemap.xml').read_text()
    
    # Check XML declaration
    assert sitemap_content.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    # Check urlset namespace
    assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in sitemap_content
    # Check closing tags
    assert sitemap_content.strip().endswith('</urlset>')
