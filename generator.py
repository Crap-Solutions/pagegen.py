#!/usr/bin/env python3
"""
Static site generator using Markdown + Jinja2
No-JS, lightweight, flexible
"""

import argparse
import os
import re
from datetime import datetime
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader


def parse_frontmatter(content):
    """
    Parse YAML frontmatter from markdown content.
    Returns (metadata, body_content) tuple.
    """
    content = content.strip()
    if content.startswith('---'):
        end = content.find('\n---', 3)
        if end != -1:
            frontmatter = content[4:end].strip()
            body = content[end + 5:].lstrip('\n')
            try:
                metadata = yaml.safe_load(frontmatter) or {}
                return metadata, body
            except yaml.YAMLError:
                # If YAML parse fails, return empty metadata with body content
                return {}, body
    return {}, content


def get_relative_css_depth(source_path, content_root, output_root):
    """
    Calculate relative path to CSS file based on source path depth.
    Returns string like '' (for root), '../', '../../', etc.
    """
    rel_path = source_path.relative_to(content_root)
    depth = len(rel_path.parent.parts)
    return '../' * depth


def get_home_link(output_path, output_root):
    """
    Get relative path prefix to homepage from output path.
    Returns '' (for root), '../', '../../', etc.
    """
    rel_path = output_path.relative_to(output_root)
    depth = len(rel_path.parent.parts)
    return '../' * depth


def get_output_path(source_path, content_root, output_root):
    """
    Determine output HTML path based on source markdown path.
    """
    rel_path = source_path.relative_to(content_root)

    # Homepage: content/index.md -> output/index.html
    if rel_path.name == 'index.md' and rel_path.parent == Path('.'):
        return output_root / 'index.html'

    # User folders: content/~user/* -> output/~user/*
    parts = list(rel_path.parts)
    if len(parts) > 1 and parts[0].startswith('~'):
        username = parts[0]

        # User index: content/~user/index.md -> output/~user/index.html
        if len(parts) == 2 and parts[-1] == 'index.md':
            return output_root / username / 'index.html'

        # Blog post: extract slug from filename
        if len(parts) == 2:
            filename = parts[-1]
            # Remove date prefix if present (YYYY-MM-DD- or YYYY_M_D-)
            slug = re.sub(r'^\d{4}[-_]\d{1,2}[-_]\d{1,2}[-_]', '', filename)
            slug = re.sub(r'\.md$', '', slug)
            return output_root / username / f'{slug}.html'

        # Nested user folder: content/~user/category/index.md -> output/~user/category.html
        if len(parts) > 2 and parts[-1] == 'index.md':
            filename = parts[-2]  # category
            filename_with_ext = f'{filename}.html'
            return output_root / username / filename_with_ext

    # Standard pages: content/about.md -> output/pages/about.html
    return output_root / 'pages' / rel_path.with_suffix('.html').name


def detect_users(content_root):
    """
    Detect user folders (~<username>) in content directory.
    Returns list of user dictionaries with name, path, index_data.
    """
    users = []

    for user_dir in sorted(content_root.glob('~*')):
        if user_dir.is_dir():
            username = user_dir.name  # includes ~ prefix
            user_index = user_dir / 'index.md'

            index_data = None
            if user_index.exists():
                with open(user_index, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                metadata, body = parse_frontmatter(raw_content)
                index_data = {
                    'path': user_index,
                    'metadata': metadata,
                    'body': body,
                }

            users.append({
                'name': username,
                'path': user_dir,
                'index_data': index_data,
            })

    return users


def scan_content(content_root):
    """
    Scan content directory for markdown files.
    Returns (pages, blog_posts_by_user, users) tuples.
    """
    pages = []
    blog_posts_by_user = {}  # {username: [posts]}

    for md_file in sorted(content_root.rglob('*.md')):
        with open(md_file, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        metadata, body = parse_frontmatter(raw_content)

        # If markdown content is empty but frontmatter exists, use empty body
        if not raw_content.startswith('---'):
            metadata = {}
            body = raw_content

        page_data = {
            'path': md_file,
            'metadata': metadata,
            'body': body,
        }

        # Check if this is a blog post in a user folder
        rel_path = md_file.relative_to(content_root)
        # Skip user index files - they're handled separately
        if len(rel_path.parts) > 1 and rel_path.parts[0].startswith('~'):
            if rel_path.name == 'index.md':
                continue  # Skip user index files
            username = rel_path.parts[0]
            if username not in blog_posts_by_user:
                blog_posts_by_user[username] = []
            blog_posts_by_user[username].append(page_data)
        else:
            pages.append(page_data)

    return pages, blog_posts_by_user


def render_markdown(content, strip_first_heading=False):
    """Convert markdown to HTML."""
    html = markdown.markdown(content, extensions=['tables', 'fenced_code'])
    if strip_first_heading:
        # Remove first h1 or h2 tag with its content
        html = re.sub(r'<h[12][^>]*>.*?</h[12]>', '', html, count=1, flags=re.DOTALL)
    return html


def get_current_year(format_str='%Y'):
    """Get current year for templates."""
    return datetime.now().strftime(format_str)


def generate_site(args):
    content_root = Path(args.content).resolve()
    output_root = Path(args.output).resolve()
    templates_root = Path(args.templates).resolve()

    # Initialize Jinja environment
    env = Environment(loader=FileSystemLoader(str(templates_root)))
    env.globals['now'] = get_current_year

    # Load config
    config_path = Path(args.config).resolve()

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Scan content
    pages, blog_posts_by_user = scan_content(content_root)

    # Detect users
    users = detect_users(content_root)

    # Group pages by section for homepage
    sections = {}
    homepage_metadata = {}

    for page in pages:
        metadata = page['metadata']
        rel_path = page['path'].relative_to(content_root)

        # Check if this is the homepage
        if rel_path.name == 'index.md' and rel_path.parent == Path('.'):
            homepage_metadata = metadata
            continue

        # Get section from metadata
        section = metadata.get('section', 'other')

        # Add to sections
        if section not in sections:
            sections[section] = []

        # Determine slug
        slug = rel_path.with_suffix('').name

        sections[section].append({
            'title': metadata.get('title', slug),
            'slug': slug,
            'metadata': metadata,
        })

    # Sort pages within sections by title
    for key in sections:
        sections[key].sort(key=lambda x: x['title'])

    # Add slug to each blog post for template use
    for username, posts in blog_posts_by_user.items():
        posts.sort(key=lambda x: str(x['metadata'].get('date', '')), reverse=True)
        for post in posts:
            filename = post['path'].name
            slug = re.sub(r'^\d{4}[-_]\d{1,2}[-_]\d{1,2}[-_]', '', filename)
            slug = re.sub(r'\.md$', '', slug)
            post['slug'] = slug

    # Process homepage
    homepage_file = content_root / 'index.md'
    if homepage_file.exists():
        with open(homepage_file, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        metadata, body = parse_frontmatter(raw_content)
        output_path = output_root / 'index.html'
        output_path.parent.mkdir(parents=True, exist_ok=True)

        css_rel_path = ''  # homepage at root
        home_link = ''

        template = env.get_template('home.html')

        # Prepare template context
        context = {
            'config': config,
            'css_rel_path': css_rel_path,
            'home_link': home_link,
            'back_link': None,
            'sections': sections,
            'users': users,
            'user_info': config.get('user', {}),
            'title': metadata.get('title', ''),
            'content': render_markdown(body, strip_first_heading=True),
            'downloads': metadata.get('downloads', []),
        }

        # Render and write
        html = template.render(**context)
        output_path.write_text(html, encoding='utf-8')
        print(f"Generated: {output_path.relative_to(output_root)}")

    # Process user index pages and blog posts
    for user in users:
        username = user['name']

        # Process user index
        if user['index_data']:
            page = user['index_data']
            source_path = page['path']
            metadata = page['metadata'].copy()
            body = page['body']

            output_path = get_output_path(source_path, content_root, output_root)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            css_rel_path = get_relative_css_depth(source_path, content_root, output_root)
            home_link = get_home_link(output_path, output_root)

            # Determine back link for header
            rel_path = source_path.relative_to(content_root)
            back_link = home_link

            # Main page header has no link
            if rel_path.name == 'index.md' and rel_path.parent == Path('.'):
                back_link = None

            template = env.get_template('blog_index.html')

            # Get posts for this user
            user_posts = blog_posts_by_user.get(username, [])

            # Prepare template context
            context = {
                'config': config,
                'css_rel_path': css_rel_path,
                'home_link': home_link,
                'back_link': back_link,
                'sections': sections,
                'posts': user_posts,
                'users': users,
                'user_info': config.get('user', {}),
            }

            # Add page-specific variables
            context['title'] = metadata.get('title', '')
            context['content'] = render_markdown(body, strip_first_heading=True)
            context['downloads'] = metadata.get('downloads', [])
            context['blog_content'] = render_markdown(body, strip_first_heading=True)

            # Render and write
            html = template.render(**context)
            output_path.write_text(html, encoding='utf-8')
            print(f"Generated: {output_path.relative_to(output_root)}")

        # Process blog posts for this user
        user_posts = blog_posts_by_user.get(username, [])
        for post in user_posts:
            source_path = post['path']
            metadata = post['metadata'].copy()
            body = post['body']

            output_path = get_output_path(source_path, content_root, output_root)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            css_rel_path = get_relative_css_depth(source_path, content_root, output_root)
            home_link = get_home_link(output_path, output_root)

            template = env.get_template('page.html')

            context = {
                'config': config,
                'css_rel_path': css_rel_path,
                'home_link': home_link,
                'back_link': 'index.html',  # blog posts link to user index
                'sections': sections,
                'posts': user_posts,
                'users': users,
                'user_info': config.get('user', {}),
                'title': metadata.get('title', ''),
                'content': render_markdown(body, strip_first_heading=True),
                'downloads': metadata.get('downloads', []),
                'metadata': metadata,  # Pass metadata for date display
            }

            html = template.render(**context)
            output_path.write_text(html, encoding='utf-8')
            print(f"Generated: {output_path.relative_to(output_root)}")

    # Process each regular page
    for page in pages:
        source_path = page['path']
        metadata = page['metadata'].copy()
        body = page['body']

        # Skip homepage (already processed)
        rel_path = source_path.relative_to(content_root)
        if rel_path.name == 'index.md' and rel_path.parent == Path('.'):
            continue

        output_path = get_output_path(source_path, content_root, output_root)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        css_rel_path = get_relative_css_depth(source_path, content_root, output_root)
        home_link = get_home_link(output_path, output_root)

        # Determine back link for header
        back_link = home_link  # default to home

        template = env.get_template('page.html')

        # Prepare template context
        context = {
            'config': config,
            'css_rel_path': css_rel_path,
            'home_link': home_link,
            'back_link': back_link,
            'sections': sections,
            'users': users,
            'user_info': config.get('user', {}),
        }

        # Add page-specific variables
        context['title'] = metadata.get('title', '')
        context['content'] = render_markdown(body)
        context['downloads'] = metadata.get('downloads', [])
        context['metadata'] = metadata  # Pass metadata for date display

        # Render and write
        html = template.render(**context)
        output_path.write_text(html, encoding='utf-8')
        print(f"Generated: {output_path.relative_to(output_root)}")

    # Copy static files
    static_root = Path(args.static)
    if static_root.exists():
        for item in static_root.rglob('*'):
            if item.is_file():
                rel = item.relative_to(static_root)
                dest = output_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(item.read_bytes())

    print(f"\nSite generated to: {output_root}")


def main():
    parser = argparse.ArgumentParser(description='Generate static site from markdown content')
    parser.add_argument('--content', default='content', help='Content directory (default: content)')
    parser.add_argument('--output', default='output', help='Output directory (default: output)')
    parser.add_argument('--config', default='config.yaml', help='Config file (default: config.yaml)')
    parser.add_argument('--static', default='static', help='Static files directory (default: static)')
    parser.add_argument('--templates', default='templates', help='Templates directory (default: templates)')

    args = parser.parse_args()
    generate_site(args)


if __name__ == '__main__':
    main()
