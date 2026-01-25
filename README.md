# pagegen.py

A no-JS static site generator using Markdown + Jinja2 templates.

## Features

- **No JavaScript** — Pure static HTML output
- **Markdown content** — Write in MD, get HTML
- **Jinja2 templates** — Flexible templating
- **YAML frontmatter** — Metadata in your content files
- **User blogs** — Support for `~user/` subdirectories with per-user blog posts
- **Date-prefixed posts** — `YYYY-MM-DD-slug.md` format
- **Config driven** — Simple `config.yaml` for site settings
- **Static assets** — Automatic copying of CSS, images, etc.

## Installation

```bash
pip install -r requirements.txt
```

### Requirements

- Python 3.7+
- jinja2 >= 3.1.0
- markdown >= 3.5.0
- pyyaml >= 6.0

## Usage

```bash
python generator.py [--content CONTENT] [--output OUTPUT] [--config CONFIG] [--static STATIC]
```

### Default locations

- `content/` — Markdown source files
- `output/` — Generated HTML
- `config.yaml` — Site configuration
- `templates/` — Jinja2 templates
- `static/` — Static assets (CSS, images, etc.)

When using pagegen.py as a submodule in another project, you typically want to override the static directory:

```bash
python lib/pagegen/generator.py --config config.yaml --static static
```

## Content Structure

```
content/
├── index.md              # Homepage
├── about.md              # Regular page -> output/pages/about.html
├── ~sigttou/
│   ├── index.md          # User index -> output/~sigttou/index.html
│   └── 2025-01-15-hello-world.md  # Blog post -> output/~sigttou/hello-world.html
└── ~otheruser/
    └── 2025-01-20-another-post.md
```

## Frontmatter

Markdown files support YAML frontmatter:

```yaml
---
title: My Page Title
section: about
date: 2025-01-15
downloads:
  - name: PDF
    url: /files/doc.pdf
---

# Content here

Write your markdown content below the frontmatter.
```

## Templates

Four templates are provided:

- `base.html` — Base layout
- `home.html` — Homepage
- `page.html` — Regular pages
- `blog_index.html` — User blog index

## License

MIT License — see [LICENSE](LICENSE) file.
