#!/usr/bin/env python3
"""
Static site generator using Markdown + Jinja2
No-JS, lightweight, flexible
"""

import argparse
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape


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
    Calculate relative path to CSS file based on output path depth.
    Returns string like '' (for root), '../', '../../', etc.
    """
    output_path = get_output_path(source_path, content_root, output_root)
    depth = len(output_path.relative_to(output_root).parent.parts)
    return '../' * depth


def get_home_link(output_path, output_root):
    """
    Get relative path prefix to homepage from output path.
    Returns '' (for root), '../', '../../', etc.
    """
    rel_path = output_path.relative_to(output_root)
    depth = len(rel_path.parent.parts)
    return '../' * depth


def extract_slug(filename, metadata=None):
    """
    Derive a URL slug for a blog post.

    Honors an explicit ``slug`` field in ``metadata`` when present; otherwise
    strips a leading date prefix (``YYYY-MM-DD-`` or ``YYYY_M_D-``) and the
    ``.md`` suffix from ``filename``.
    """
    if metadata and metadata.get('slug'):
        return str(metadata['slug'])
    slug = re.sub(r'^\d{4}[-_]\d{1,2}[-_]\d{1,2}[-_]', '', filename)
    slug = re.sub(r'\.md$', '', slug)
    return slug


def get_output_path(source_path, content_root, output_root, metadata=None):
    """
    Determine output HTML path based on source markdown path.

    When ``metadata`` is supplied, an explicit ``slug`` is honored for blog
    posts (otherwise the slug is derived from the filename).
    """
    rel_path = source_path.relative_to(content_root)

    # Homepage: content/index.md -> output/index.html
    if rel_path.name == 'index.md' and rel_path.parent == Path('.'):
        return output_root / 'index.html'

    # Custom error page: content/404.md -> output/404.html
    if rel_path.name == '404.md' and rel_path.parent == Path('.'):
        return output_root / '404.html'

    # User folders: content/~user/* -> output/~user/*
    parts = list(rel_path.parts)
    if len(parts) > 1 and parts[0].startswith('~'):
        username = parts[0]

        # User index: content/~user/index.md -> output/~user/index.html
        if len(parts) == 2 and parts[-1] == 'index.md':
            return output_root / username / 'index.html'

        # Blog post: honor metadata['slug'] if present, else derive from filename
        if len(parts) == 2:
            slug = extract_slug(parts[-1], metadata)
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


def generate_sitemap(output_root, content_root, config, pages, blog_posts_by_user, users):
    """Generate sitemap.xml with all pages."""
    base_url = config['site']['url']
    urls = []
    current_date = datetime.now().strftime('%Y-%m-%d')

    # Add homepage
    urls.append({'loc': base_url + '/', 'lastmod': current_date, 'priority': '1.0', 'changefreq': 'daily'})

    # Add regular pages
    for page in pages:
        rel_path = page['path'].relative_to(content_root)
        # Skip homepage and the custom 404 page
        if rel_path.name == 'index.md' and rel_path.parent == Path('.'):
            continue
        if rel_path.name == '404.md' and rel_path.parent == Path('.'):
            continue

        output_path = get_output_path(page['path'], content_root, output_root, page.get('metadata'))
        url_path = output_path.relative_to(output_root).as_posix()
        urls.append({
            'loc': base_url + '/' + url_path,
            'lastmod': current_date,
            'priority': '0.8',
            'changefreq': 'weekly'
        })

    # Add user index pages
    for user in users:
        url_path = user['name'] + '/index.html'
        urls.append({
            'loc': base_url + '/' + url_path,
            'lastmod': current_date,
            'priority': '0.7',
            'changefreq': 'weekly'
        })

    # Add blog posts
    for username, posts in blog_posts_by_user.items():
        for post in posts:
            slug = extract_slug(post['path'].name, post.get('metadata'))
            url_path = username + '/' + slug + '.html'
            post_date = post.get('metadata', {}).get('date', current_date)
            urls.append({
                'loc': base_url + '/' + url_path,
                'lastmod': post_date,
                'priority': '0.6',
                'changefreq': 'monthly'
            })

    # Generate XML via ElementTree so all values are properly escaped.
    ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('', ns)
    urlset = ET.Element(f'{{{ns}}}urlset')
    for url in urls:
        url_el = ET.SubElement(urlset, f'{{{ns}}}url')
        ET.SubElement(url_el, f'{{{ns}}}loc').text = url['loc']
        ET.SubElement(url_el, f'{{{ns}}}lastmod').text = str(url['lastmod'])
        ET.SubElement(url_el, f'{{{ns}}}changefreq').text = url['changefreq']
        ET.SubElement(url_el, f'{{{ns}}}priority').text = str(url['priority'])

    sitemap_path = output_root / 'sitemap.xml'
    ET.ElementTree(urlset).write(sitemap_path, encoding='utf-8', xml_declaration=True)
    print(f"Generated: {sitemap_path.relative_to(output_root)}")


def format_rss_date(date_value):
    """
    Format a date value as an RFC 822 string for an RSS ``<pubDate>``.

    Accepts a ``datetime``/``date`` object or a string. Returns ``None`` for an
    empty/unparseable value so the caller can omit the element.
    """
    if hasattr(date_value, 'strftime'):
        return date_value.strftime('%a, %d %b %Y 00:00:00 +0000')
    text = str(date_value).strip()
    if not text:
        return None
    try:
        parsed = datetime.strptime(text[:10], '%Y-%m-%d')
    except ValueError:
        return None
    return parsed.strftime('%a, %d %b %Y 00:00:00 +0000')


def generate_feed(output_root, content_root, config, blog_posts_by_user):
    """Generate an RSS 2.0 feed (feed.xml) from all blog posts across users."""
    site = config.get('site', {})
    base_url = str(site.get('url', '')).rstrip('/')
    title = site.get('title', '')
    description = site.get('description', '')
    build_date = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')

    # Collect posts from all users, newest first.
    entries = []
    for username, posts in blog_posts_by_user.items():
        for post in posts:
            metadata = post.get('metadata', {})
            slug = extract_slug(post['path'].name, metadata)
            url_path = username + '/' + slug + '.html'
            link = base_url + '/' + url_path
            raw_date = metadata.get('date', '')
            entries.append({
                'title': metadata.get('title', slug),
                'link': link,
                # Sort by the raw date (ISO strings / date objects compare
                # chronologically); the RFC 822 string does not.
                'sort_key': str(raw_date),
                'pub_date': format_rss_date(raw_date),
                'description': metadata.get('description', ''),
            })
    entries.sort(key=lambda e: e['sort_key'], reverse=True)

    rss = ET.Element('rss', attrib={'version': '2.0'})
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = title
    ET.SubElement(channel, 'link').text = base_url + '/'
    ET.SubElement(channel, 'description').text = description
    ET.SubElement(channel, 'lastBuildDate').text = build_date

    for entry in entries:
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = entry['title']
        ET.SubElement(item, 'link').text = entry['link']
        ET.SubElement(item, 'guid', attrib={'isPermaLink': 'true'}).text = entry['link']
        if entry['pub_date']:
            ET.SubElement(item, 'pubDate').text = entry['pub_date']
        if entry['description']:
            ET.SubElement(item, 'description').text = entry['description']

    feed_path = output_root / 'feed.xml'
    ET.ElementTree(rss).write(feed_path, encoding='utf-8', xml_declaration=True)
    print(f"Generated: {feed_path.relative_to(output_root)}")


def generate_site(args):
    content_root = Path(args.content).resolve()
    output_root = Path(args.output).resolve()
    templates_root = Path(args.templates).resolve()

    # Optionally wipe the output directory before regenerating so deleted
    # content does not leave stale files behind.
    if getattr(args, 'clean', False) and output_root.exists():
        protected = {content_root, templates_root}
        if output_root in protected:
            raise SystemExit(f"Refusing to --clean {output_root}: it is a source directory")
        for child in output_root.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()

    # Initialize Jinja environment (autoescape protects every variable; the
    # trusted Markdown body is still inserted via the `| safe` filter).
    env = Environment(
        loader=FileSystemLoader(str(templates_root)),
        autoescape=select_autoescape(['html', 'xml']),
    )
    env.globals['now'] = get_current_year

    # Load config
    config_path = Path(args.config).resolve()

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    base_url = str(config.get('site', {}).get('url', '')).rstrip('/')

    # Track written outputs so two content files can never silently overwrite
    # the same generated page.
    seen_outputs = set()

    def page_url_of(output_path):
        return output_path.relative_to(output_root).as_posix()

    def write_output(output_path, html):
        rel = page_url_of(output_path)
        if rel in seen_outputs:
            raise ValueError(
                f"Output path collision: '{rel}' is generated by more than one content file"
            )
        seen_outputs.add(rel)
        output_path.write_text(html, encoding='utf-8')
        print(f"Generated: {rel}")

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
        # Skip the custom 404 page (rendered separately, not a section entry)
        if rel_path.name == '404.md' and rel_path.parent == Path('.'):
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

    # Resolve a slug for each blog post (honors metadata['slug']) for template use
    for username, posts in blog_posts_by_user.items():
        posts.sort(key=lambda x: str(x['metadata'].get('date', '')), reverse=True)
        for post in posts:
            post['slug'] = extract_slug(post['path'].name, post['metadata'])

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

        # Collect recent blog posts from all users
        recent_posts = []
        for username, posts in blog_posts_by_user.items():
            for post in posts:
                post['username'] = username
                recent_posts.append(post)
        # Sort by date (newest first)
        recent_posts.sort(key=lambda x: str(x['metadata'].get('date', '')), reverse=True)

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
            'recent_posts': recent_posts[:5],  # Limit to 5 recent posts
            'page_url': page_url_of(output_path),
            'canonical_url': base_url + '/' + page_url_of(output_path),
        }

        # Render and write
        html = template.render(**context)
        write_output(output_path, html)

    # Process the custom 404 page (if present).
    #
    # ErrorDocument serves /404.html under the *original* (bogus) URL, so the
    # browser resolves relative asset links against that bogus path and they
    # 404. Root-absolute paths (e.g. "/crap.css") resolve against the site root
    # instead, so the page renders correctly from any URL.
    error_file = content_root / '404.md'
    if error_file.exists():
        with open(error_file, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        metadata, body = parse_frontmatter(raw_content)
        output_path = output_root / '404.html'
        output_path.parent.mkdir(parents=True, exist_ok=True)

        template = env.get_template('page.html')

        context = {
            'config': config,
            'css_rel_path': '/',       # root-absolute: "/crap.css"
            'home_link': '/',          # root-absolute: "/index.html"
            'back_link': '/',          # header link back to site root
            'sections': sections,
            'users': users,
            'user_info': config.get('user', {}),
            'title': metadata.get('title', ''),
            'content': render_markdown(body),
            'downloads': metadata.get('downloads', []),
            'metadata': metadata,
            'page_url': page_url_of(output_path),
            'canonical_url': base_url + '/' + page_url_of(output_path),
        }

        html = template.render(**context)
        write_output(output_path, html)

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
            context['page_url'] = page_url_of(output_path)
            context['canonical_url'] = base_url + '/' + context['page_url']

            # Render and write
            html = template.render(**context)
            write_output(output_path, html)

        # Process blog posts for this user
        user_posts = blog_posts_by_user.get(username, [])
        for post in user_posts:
            source_path = post['path']
            metadata = post['metadata'].copy()
            body = post['body']

            output_path = get_output_path(source_path, content_root, output_root, metadata)
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
                'page_url': page_url_of(output_path),
                'canonical_url': base_url + '/' + page_url_of(output_path),
            }

            html = template.render(**context)
            write_output(output_path, html)

    # Process each regular page
    for page in pages:
        source_path = page['path']
        metadata = page['metadata'].copy()
        body = page['body']

        # Skip homepage (already processed)
        rel_path = source_path.relative_to(content_root)
        if rel_path.name == 'index.md' and rel_path.parent == Path('.'):
            continue
        # Skip the custom 404 page (rendered separately with absolute paths)
        if rel_path.name == '404.md' and rel_path.parent == Path('.'):
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
        context['page_url'] = page_url_of(output_path)
        context['canonical_url'] = base_url + '/' + context['page_url']

        # Render and write
        html = template.render(**context)
        write_output(output_path, html)

    # Copy static files
    static_root = Path(args.static)
    if static_root.exists():
        for item in static_root.rglob('*'):
            if item.is_file():
                rel = item.relative_to(static_root)
                dest = output_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(item.read_bytes())

    # Generate sitemap
    generate_sitemap(output_root, content_root, config, pages, blog_posts_by_user, users)

    # Generate RSS feed
    generate_feed(output_root, content_root, config, blog_posts_by_user)

    print(f"\nSite generated to: {output_root}")


def main():
    parser = argparse.ArgumentParser(description='Generate static site from markdown content')
    parser.add_argument('--content', default='content', help='Content directory (default: content)')
    parser.add_argument('--output', default='output', help='Output directory (default: output)')
    parser.add_argument('--config', default='config.yaml', help='Config file (default: config.yaml)')
    parser.add_argument('--static', default='static', help='Static files directory (default: static)')
    parser.add_argument('--templates', default='templates', help='Templates directory (default: templates)')
    parser.add_argument('--clean', action='store_true', help='Remove output directory contents before generating')

    args = parser.parse_args()
    generate_site(args)


if __name__ == '__main__':
    main()
