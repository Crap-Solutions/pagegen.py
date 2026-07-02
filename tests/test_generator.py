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
    generate_site,
    extract_slug,
    generate_feed,
    format_rss_date,
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
    
    # Check XML declaration (format varies across XML emitters)
    assert sitemap_content.startswith('<?xml version')
    # Check urlset namespace
    assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in sitemap_content
    # Check closing tags
    assert sitemap_content.strip().endswith('</urlset>')


# ============================================================================
# extract_slug / metadata slug tests
# ============================================================================

def test_extract_slug_strips_date_prefix():
    """Slug derived from filename with date prefix"""
    assert extract_slug('2025-01-25-hello-world.md') == 'hello-world'


def test_extract_slug_strips_underscore_date():
    """Slug derived from filename with underscore date prefix"""
    assert extract_slug('2025_1_25-hello-world.md') == 'hello-world'


def test_extract_slug_no_date_prefix():
    """Filename without date prefix keeps its basename"""
    assert extract_slug('my-post.md') == 'my-post'


def test_extract_slug_honors_metadata_slug():
    """Explicit slug in metadata takes precedence over the filename"""
    assert extract_slug('2025-01-25-ignored.md', {'slug': 'custom-slug'}) == 'custom-slug'


def test_extract_slug_ignores_empty_metadata_slug():
    """An empty slug in metadata falls back to the filename"""
    assert extract_slug('2025-01-25-hello.md', {'slug': ''}) == 'hello'


def test_get_output_path_honors_metadata_slug():
    """Blog post output path honors an explicit slug from metadata"""
    content_root = Path('/content')
    output_root = Path('/output')

    source = content_root / '~user/2025-01-25-filename-slug.md'
    metadata = {'slug': 'metadata-slug'}
    result = get_output_path(source, content_root, output_root, metadata)

    assert result == output_root / '~user' / 'metadata-slug.html'


# ============================================================================
# generate_site: autoescape, collisions, sitemap escaping
# ============================================================================

def _write_config(path):
    path.write_text(
        "site:\n"
        "  title: Test\n"
        "  description: desc\n"
        "  url: https://example.com\n"
        "css_filename: test.css\n",
        encoding='utf-8',
    )


def _make_args(content, output, config, templates):
    from argparse import Namespace
    return Namespace(
        content=str(content),
        output=str(output),
        config=str(config),
        static='__no_such_static__',
        templates=str(templates),
        clean=False,
    )


def test_generate_site_escapes_frontmatter_title(tmp_path):
    """Autoescape must escape HTML in frontmatter fields (not the | safe body)"""
    repo = Path(__file__).parent.parent
    content = tmp_path / 'content'
    content.mkdir()
    # Malicious title; harmless body
    (content / 'index.md').write_text(
        '---\ntitle: <script>alert(1)</script>\n---\nhello world',
        encoding='utf-8',
    )
    config = tmp_path / 'config.yaml'
    _write_config(config)
    output = tmp_path / 'output'

    generate_site(_make_args(content, output, config, repo / 'templates'))

    html = (output / 'index.html').read_text(encoding='utf-8')
    # Raw script tag must NOT appear; it must be HTML-escaped
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;' in html


def test_generate_site_detects_output_collision(tmp_path):
    """Two content files mapping to the same output must fail loudly"""
    repo = Path(__file__).parent.parent
    content = tmp_path / 'content'
    (content / 'a').mkdir(parents=True)
    (content / 'b').mkdir(parents=True)
    # Both flatten to output/pages/about.html
    (content / 'a' / 'about.md').write_text('---\ntitle: A\n---\n# A', encoding='utf-8')
    (content / 'b' / 'about.md').write_text('---\ntitle: B\n---\n# B', encoding='utf-8')
    config = tmp_path / 'config.yaml'
    _write_config(config)
    output = tmp_path / 'output'

    with pytest.raises(ValueError, match='Output path collision'):
        generate_site(_make_args(content, output, config, repo / 'templates'))


def test_generate_site_clean_wipes_output(tmp_path):
    """--clean removes stale files left from a previous build"""
    repo = Path(__file__).parent.parent
    content = tmp_path / 'content'
    content.mkdir()
    (content / 'index.md').write_text('---\ntitle: Home\n---\nhome', encoding='utf-8')
    config = tmp_path / 'config.yaml'
    _write_config(config)
    output = tmp_path / 'output'
    output.mkdir()
    stale = output / 'stale.html'
    stale.write_text('old', encoding='utf-8')

    args = _make_args(content, output, config, repo / 'templates')
    args.clean = True
    generate_site(args)

    assert not stale.exists()
    assert (output / 'index.html').exists()


def test_homepage_lists_recent_posts_with_rss_link(tmp_path):
    """Homepage renders up to 5 newest posts and links to the RSS feed"""
    repo = Path(__file__).parent.parent
    content = tmp_path / 'content'
    content.mkdir()
    (content / 'index.md').write_text('---\ntitle: Home\n---\nhome', encoding='utf-8')
    # Six posts: only the five newest should appear (newest first).
    user_dir = content / '~alice'
    user_dir.mkdir()
    for i in range(1, 7):
        (user_dir / f'2025-01-2{i}-post{i}.md').write_text(
            f'---\ntitle: Post {i}\ndate: 2025-01-2{i}\n---\nbody {i}', encoding='utf-8')
    config = tmp_path / 'config.yaml'
    _write_config(config)
    output = tmp_path / 'output'

    generate_site(_make_args(content, output, config, repo / 'templates'))

    html = (output / 'index.html').read_text(encoding='utf-8')
    # RSS subscribe link points at the generated feed
    assert 'href="https://example.com/feed.xml"' in html
    assert '📰 RSS' in html
    # Newest five posts present, oldest (post1) omitted by the 5-item cap
    assert 'Post 6' in html and 'Post 2' in html
    assert 'Post 1' not in html
    # Order is newest-first (Post 6 before Post 2)
    assert html.index('Post 6') < html.index('Post 2')
    # Post links are relative to the user folder
    assert 'href="~alice/post6.html"' in html


def test_sitemap_escapes_special_characters(tmp_path):
    """A base URL containing '&' must produce valid, escaped XML"""
    content_root = tmp_path / 'content'
    output_root = tmp_path / 'output'
    content_root.mkdir()
    output_root.mkdir()

    config = {'site': {'url': 'https://example.com/a&b'}}
    generate_sitemap(output_root, content_root, config, [], {}, [])

    sitemap = (output_root / 'sitemap.xml').read_text(encoding='utf-8')
    # '&' in the URL must be escaped to '&amp;', never a raw '&'
    assert 'https://example.com/a&amp;b/' in sitemap
    # Must parse as well-formed XML
    import xml.etree.ElementTree as ET
    ET.fromstring(sitemap)


# ============================================================================
# format_rss_date tests
# ============================================================================

def test_format_rss_date_from_string():
    """ISO date string -> RFC 822"""
    assert format_rss_date('2025-01-25') == 'Sat, 25 Jan 2025 00:00:00 +0000'


def test_format_rss_date_from_date_object():
    """datetime.date object -> RFC 822"""
    from datetime import date
    assert format_rss_date(date(2025, 1, 25)) == 'Sat, 25 Jan 2025 00:00:00 +0000'


def test_format_rss_date_empty_returns_none():
    """Empty / unparseable -> None (caller omits pubDate)"""
    assert format_rss_date('') is None
    assert format_rss_date('not-a-date') is None


# ============================================================================
# generate_feed tests
# ============================================================================

def test_generate_feed_creates_file(tmp_path):
    """feed.xml is created and is well-formed RSS"""
    import xml.etree.ElementTree as ET
    output_root = tmp_path / 'output'
    output_root.mkdir()
    config = {'site': {'url': 'https://example.com', 'title': 'T', 'description': 'd'}}
    generate_feed(output_root, tmp_path, config, {})
    feed = (output_root / 'feed.xml')
    assert feed.exists()
    ET.fromstring(feed.read_text())  # well-formed


def test_generate_feed_lists_posts_chronological(tmp_path):
    """Posts appear newest-first; title/channel populated"""
    import xml.etree.ElementTree as ET
    output_root = tmp_path / 'output'
    output_root.mkdir()
    config = {'site': {'url': 'https://example.com', 'title': 'MySite', 'description': 'd'}}
    posts = {
        '~u': [
            {'path': Path('/c/~u/2025-01-25-old.md'), 'metadata': {'title': 'Old', 'date': '2025-01-25'}},
            {'path': Path('/c/~u/2025-01-28-new.md'), 'metadata': {'title': 'New', 'date': '2025-01-28'}},
        ]
    }
    generate_feed(output_root, tmp_path, config, posts)
    root = ET.fromstring((output_root / 'feed.xml').read_text())
    titles = [i.find('title').text for i in root.iter('item')]
    assert titles == ['New', 'Old']  # newest first
    assert root.find('channel/title').text == 'MySite'


def test_generate_feed_escapes_special_characters(tmp_path):
    """A title with '&' is escaped in the XML"""
    import xml.etree.ElementTree as ET
    output_root = tmp_path / 'output'
    output_root.mkdir()
    config = {'site': {'url': 'https://example.com', 'title': 'T', 'description': 'd'}}
    posts = {'~u': [{'path': Path('/c/~u/2025-01-25-a.md'),
                     'metadata': {'title': 'A & B', 'date': '2025-01-25'}}]}
    generate_feed(output_root, tmp_path, config, posts)
    root = ET.fromstring((output_root / 'feed.xml').read_text())
    assert root.find('channel/item/title').text == 'A & B'  # parsed back correctly


# ============================================================================
# 404 page routing
# ============================================================================

def test_get_output_path_404():
    """Top-level content/404.md -> output/404.html"""
    content_root = Path('/content')
    output_root = Path('/output')
    result = get_output_path(content_root / '404.md', content_root, output_root)
    assert result == output_root / '404.html'


def test_404_excluded_from_sections_and_sitemap(tmp_path):
    """404.md renders to 404.html but is not a section entry or in the sitemap"""
    import xml.etree.ElementTree as ET
    repo = Path(__file__).parent.parent
    content = tmp_path / 'content'
    content.mkdir()
    (content / 'index.md').write_text('---\ntitle: Home\n---\nhome', encoding='utf-8')
    (content / '404.md').write_text('---\ntitle: 404\n---\nmissing', encoding='utf-8')
    config = tmp_path / 'config.yaml'
    config.write_text(
        "site:\n  title: T\n  description: d\n  url: https://example.com\ncss_filename: t.css\n",
        encoding='utf-8',
    )
    output = tmp_path / 'output'
    from argparse import Namespace
    generate_site(Namespace(content=str(content), output=str(output), config=str(config),
                            static='__none__', templates=str(repo / 'templates'), clean=False))

    assert (output / '404.html').exists()         # rendered
    homepage = (output / 'index.html').read_text()
    assert 'pages/404.html' not in homepage        # not a section entry on the homepage
    sitemap = (output / 'sitemap.xml').read_text()
    assert '404.html' not in sitemap               # not in sitemap
    ET.fromstring(sitemap)                          # still well-formed


def test_404_uses_absolute_asset_paths(tmp_path):
    """ErrorDocument serves /404.html under the bogus URL, so the 404 page must
    reference CSS/favicon/home with root-absolute paths (not relative ones that
    would resolve against the missing URL and 404 themselves)."""
    repo = Path(__file__).parent.parent
    content = tmp_path / 'content'
    content.mkdir()
    (content / 'index.md').write_text('---\ntitle: Home\n---\nhome', encoding='utf-8')
    (content / '404.md').write_text('---\ntitle: 404\n---\nmissing', encoding='utf-8')
    config = tmp_path / 'config.yaml'
    config.write_text(
        "site:\n  title: T\n  description: d\n  url: https://example.com\ncss_filename: t.css\n",
        encoding='utf-8',
    )
    output = tmp_path / 'output'
    from argparse import Namespace
    generate_site(Namespace(content=str(content), output=str(output), config=str(config),
                            static='__none__', templates=str(repo / 'templates'), clean=False))

    page = (output / '404.html').read_text()
    # Root-absolute asset references (ErrorDocument serves the page under the
    # bogus URL, so relative links would resolve against that URL and 404).
    assert 'href="/t.css"' in page               # CSS absolute
    assert 'href="/index.html"' in page          # footer Home link absolute
    # No relative asset references that would break under a bogus URL
    assert 'href="t.css"' not in page

    # Sanity: homepage (contrast) keeps its relative paths
    home = (output / 'index.html').read_text()
    assert 'href="t.css"' in home
