#!/usr/bin/env python3
"""Build index.html from project.md and the local HTML template."""

from __future__ import annotations

import html
import hashlib
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlunparse

try:
    import yaml
    from markdown_it import MarkdownIt
except ImportError as exc:
    raise SystemExit(
        "Missing dependency. Run: python3 -m pip install -r requirements.txt"
    ) from exc


ROOT = Path(__file__).resolve().parent
CONTAINER_RE = re.compile(
    r"^:::\s*([a-zA-Z][\w-]*)\s*$\n(.*?)^:::\s*$",
    re.MULTILINE | re.DOTALL,
)
CAROUSEL_RE = re.compile(
    r"^::::\s*carousel\s*$\n(.*?)^::::\s*$",
    re.MULTILINE | re.DOTALL,
)
CAROUSEL_CELL_RE = re.compile(
    r"^:::\s*carousel-cell\s*$\n(.*?)^:::\s*$",
    re.MULTILINE | re.DOTALL,
)
MEDIA_DIRECTIVE_RE = re.compile(r"@\[([a-zA-Z][\w-]*)\]\(\s*(.*?)\s*\)")
SUPERSCRIPT_RE = re.compile(r"\^([0-9]+)\^")
ICON_TAG_RE = re.compile(r'<i\s+class="fa\s+([^" ]+)"[^>]*>\s*</i>', re.IGNORECASE)
BUTTON_LINK_RE = re.compile(
    r'\[<i class="fa fa-([^"]+)"[^>]*></i>\s*([^\]]+)\]\(([^)]+)\)'
)
BUTTON_ICON_MAP = {
    "file-pdf-o": "fas fa-file-pdf",
    "file-alt": "fas fa-file-alt",
    "youtube-play": "fab fa-youtube",
    "github": "fab fa-github",
    "chart-bar": "fas fa-chart-bar",
    "results": "fas fa-chart-bar",
}
SECTION_LAYOUT = {
    "demo": "teaser",
    "abstract": "abstract",
    "video-gallery": "carousel-band",
    "citation": "bibtex",
}
VIDEO_PARAGRAPH_RE = re.compile(
    r'<p>\s*(?:<a href="(?P<link>[^"]+\.(?:mp4|webm|ogg)(?:[?#][^"]*)?)"(?:[^>]*)>(?P<link_label>.*?)</a>|'
    r'<img src="(?P<image>[^"]+\.(?:mp4|webm|ogg))" alt="(?P<image_label>.*?)"\s*/?>)\s*</p>',
    re.IGNORECASE | re.DOTALL,
)
NAV_CONTAINER_RE = re.compile(
    r"^:::\s*nav\s*$\n(.*?)^:::\s*$",
    re.MULTILINE | re.DOTALL,
)


def parse_project(path: Path) -> tuple[dict[str, str], str]:
    source = path.read_text(encoding="utf-8")
    if not source.startswith("---\n"):
        return {}, source
    _, front_matter, body = source.split("---\n", 2)
    metadata = yaml.safe_load(front_matter) or {}
    return {str(key): "" if value is None else str(value) for key, value in metadata.items()}, body


def slugify(text: str) -> str:
    plain = re.sub(r"<[^>]+>", "", text)
    plain = html.unescape(plain).strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", plain).strip("-")


def add_heading_ids(markup: str) -> str:
    return markup


def render_button_links(content: str) -> str:
    buttons: list[str] = []
    for icon_key, label, href in BUTTON_LINK_RE.findall(content):
        icon_class = BUTTON_ICON_MAP.get(icon_key, "fas fa-link")
        safe_href = html.escape(href, quote=True)
        safe_label = html.escape(label.strip(), quote=True)
        external = ""
        if href.startswith(("http://", "https://")):
            external = ' class="external-link button is-normal is-rounded is-dark" target="_blank" rel="noopener noreferrer"'
        else:
            external = ' class="button is-normal is-rounded is-dark"'
        buttons.append(
            f'<span class="link-block">'
            f'<a href="{safe_href}"{external}>'
            f'<span class="icon"><i class="{icon_class}"></i></span>'
            f"<span>{safe_label}</span>"
            f"</a></span>"
        )
    if not buttons:
        return ""
    return (
        '<div class="column has-text-centered">'
        f'<div class="publication-links">{"".join(buttons)}</div>'
        "</div>"
    )


def render_navigation(markdown: MarkdownIt, content: str) -> str:
    """Render navigation links declared in a project.md nav container."""
    rendered = markdown.render(content.strip())
    links: list[str] = []
    for match in re.finditer(r"<a\b(?P<attrs>[^>]*)>(?P<label>.*?)</a>", rendered, re.DOTALL | re.IGNORECASE):
        attrs = match.group("attrs")
        href_match = re.search(r'\bhref="([^"]*)"', attrs, re.IGNORECASE)
        if not href_match:
            continue
        href = href_match.group(1)
        label = match.group("label").strip()
        safe_href = html.escape(href, quote=True)
        external = href.startswith(("http://", "https://"))
        target = ' target="_blank" rel="noopener noreferrer"' if external else ""
        links.append(
            f'<a class="navbar-item" href="{safe_href}"{target}>{label}</a>'
        )
    if not links:
        return ""
    return (
        '<nav class="navbar project-navbar" role="navigation" aria-label="Project navigation">'
        '<div class="navbar-menu is-active"><div class="navbar-start">'
        + "".join(links)
        + "</div></div></nav>"
    )


def normalize_headings(content: str) -> str:
    content = re.sub(
        r"<h1>(.*?)</h1>",
        r'<h1 class="title is-1 publication-title">\1</h1>',
        content,
        count=1,
        flags=re.DOTALL,
    )
    content = re.sub(
        r"<h2>(.*?)</h2>",
        r'<h2 class="title is-3">\1</h2>',
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r"<h3>(.*?)</h3>",
        r'<h3 class="title is-4">\1</h3>',
        content,
        flags=re.DOTALL,
    )
    return content


def wrap_hero(content: str) -> str:
    content = normalize_headings(content)
    content = content.replace(
        'class="markdown-container author-container"',
        'class="is-size-5 publication-authors"',
    )
    content = content.replace(
        'class="markdown-container institution-container"',
        'class="is-size-5 publication-authors"',
    )
    return (
        '<section class="hero">\n'
        '  <div class="hero-body">\n'
        '    <div class="container is-max-desktop">\n'
        '      <div class="columns is-centered">\n'
        '        <div class="column has-text-centered">\n'
        f"{content}\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </div>\n"
        "</section>"
    )


def wrap_section(section_id: str, heading: str, body: str) -> str:
    layout = SECTION_LAYOUT.get(section_id, "default")
    body = normalize_headings(body)
    safe_id = html.escape(section_id, quote=True)

    if layout == "teaser":
        inner = re.sub(r"<h2(?: class=\"title is-3\")?>Demo</h2>\s*", "", body, count=1)
        return (
            f'<section class="hero teaser" id="{safe_id}">\n'
            '  <div class="container is-max-desktop">\n'
            '    <div class="hero-body">\n'
            f"{inner}\n"
            "    </div>\n"
            "  </div>\n"
            "</section>"
        )

    if layout == "abstract":
        inner = re.sub(r"<h2 class=\"title is-3\">Abstract</h2>\s*", "", body, count=1)
        return (
            f'<section class="section" id="{safe_id}">\n'
            '  <div class="container is-max-desktop">\n'
            '    <div class="columns is-centered has-text-centered">\n'
            '      <div class="column is-four-fifths">\n'
            '        <h2 class="title is-3">Abstract</h2>\n'
            '        <div class="content has-text-justified">\n'
            f"{inner}\n"
            "        </div>\n"
            "      </div>\n"
            "    </div>\n"
            "  </div>\n"
            "</section>"
        )

    if layout == "carousel-band":
        inner = re.sub(r"<h2 class=\"title is-3\">.*?</h2>\s*", "", body, count=1, flags=re.DOTALL)
        return (
            f'<section class="hero is-light is-small" id="{safe_id}">\n'
            '  <div class="hero-body">\n'
            '    <div class="container">\n'
            f'      <h2 class="title is-3 has-text-centered">{html.escape(heading)}</h2>\n'
            f"{inner}\n"
            "    </div>\n"
            "  </div>\n"
            "</section>"
        )

    if layout == "bibtex":
        inner = re.sub(r"<h2 class=\"title is-3\">Citation</h2>\s*", "", body, count=1)
        inner = re.sub(
            r"<p>Use the following entry when citing the project\. Update the author and venue fields when the paper metadata is final\.</p>\s*",
            "",
            inner,
            count=1,
        )
        return (
            f'<section class="section" id="{safe_id}">\n'
            '  <div class="container is-max-desktop content">\n'
            '    <h2 class="title">BibTeX</h2>\n'
            f"{inner}\n"
            "  </div>\n"
            "</section>"
        )

    return (
        f'<section class="section" id="{safe_id}">\n'
        '  <div class="container is-max-desktop">\n'
        '    <div class="columns is-centered">\n'
        '      <div class="column is-full-width">\n'
        '        <div class="content">\n'
        f"{body}\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </div>\n"
        "</section>"
    )


def inject_button_links(content: str, button_markup: str) -> str:
    if button_markup:
        content = re.sub(
            r'<div class="markdown-container button-container">\s*<p>.*?</p>\s*</div>',
            button_markup,
            content,
            flags=re.DOTALL,
        )
    else:
        content = re.sub(
            r'<div class="markdown-container button-container">\s*<p>.*?</p>\s*</div>',
            "",
            content,
            flags=re.DOTALL,
        )
    return content


def make_sections(markup: str, button_source: str = "") -> str:
    parts = re.split(r"(?=<h2(?:\s|>))", markup)
    sections: list[str] = []
    button_markup = render_button_links(button_source)

    hero = parts[0].strip()
    if hero:
        hero = inject_button_links(hero, button_markup)
        sections.append(wrap_hero(hero))

    for part in parts[1:]:
        if not part.strip():
            continue
        heading_match = re.search(r"<h2>(.*?)</h2>", part, flags=re.DOTALL)
        if not heading_match:
            continue
        heading = re.sub(r"<[^>]+>", "", heading_match.group(1))
        heading = html.unescape(heading).strip()
        section_id = slugify(heading)
        sections.append(wrap_section(section_id, heading, part.strip()))

    return "\n\n".join(sections)


def replace_video_paragraphs(markup: str) -> str:
    def replace(match: re.Match[str]) -> str:
        url = match.group("link") or match.group("image")
        label = match.group("link_label") or match.group("image_label") or "Video"
        return (
            f'<video class="markdown-video" controls muted loop playsinline preload="metadata" '
            f'src="{html.escape(url, quote=True)}" aria-label="{html.escape(label, quote=True)}">'
            f'<a href="{html.escape(url, quote=True)}">Open the video.</a></video>'
        )

    return VIDEO_PARAGRAPH_RE.sub(replace, markup)


def youtube_id(value: str) -> str:
    parsed = urlparse(value)
    if parsed.netloc.endswith("youtu.be"):
        return parsed.path.strip("/")
    if "youtube" in parsed.netloc:
        return parse_qs(parsed.query).get("v", [parsed.path.rsplit("/", 1)[-1]])[0]
    return value.strip()


def cache_bust_local_media(value: str) -> str:
    """Add a content hash so replaced local media cannot reuse an old URL."""
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or parsed.path.startswith(("#", "data:")):
        return value
    local_path = ROOT / parsed.path
    if not local_path.is_file():
        return value
    digest = hashlib.sha256(local_path.read_bytes()).hexdigest()[:12]
    query = f"{parsed.query}&v={digest}" if parsed.query else f"v={digest}"
    return urlunparse(parsed._replace(query=query))


def embed_media(service: str, value: str) -> str | None:
    value = cache_bust_local_media(value) if service.lower() == "video" else value
    safe_value = html.escape(value, quote=True)
    service = service.lower()
    if service == "video":
        return (
            f'<video class="markdown-video" controls muted loop playsinline preload="metadata" src="{safe_value}">'
            f'<a href="{safe_value}">Open the video.</a></video>'
        )
    if service == "audio":
        return f'<audio class="markdown-audio" controls preload="metadata" src="{safe_value}"></audio>'
    if service == "youtube":
        video_id = html.escape(youtube_id(value), quote=True)
        return f'<div class="embed-video"><iframe src="https://www.youtube-nocookie.com/embed/{video_id}" title="YouTube video" loading="lazy" allowfullscreen></iframe></div>'
    if service == "vimeo":
        video_id = html.escape(value.rstrip("/").rsplit("/", 1)[-1], quote=True)
        return f'<div class="embed-video"><iframe src="https://player.vimeo.com/video/{video_id}" title="Vimeo video" loading="lazy" allowfullscreen></iframe></div>'
    if service == "bilibili":
        video_id = html.escape(value, quote=True)
        return f'<div class="embed-video"><iframe src="https://player.bilibili.com/player.html?bvid={video_id}" title="Bilibili video" loading="lazy" allowfullscreen></iframe></div>'
    return None


def replace_media_directives(markdown: MarkdownIt, body: str) -> tuple[str, list[str]]:
    media_blocks: list[str] = []

    def replace(match: re.Match[str]) -> str:
        block = embed_media(match.group(1), match.group(2))
        if block is None:
            return match.group(0)
        index = len(media_blocks)
        media_blocks.append(block)
        return f"\n\n<!-- MEDIA_DIRECTIVE_{index} -->\n\n"

    body_with_markers = MEDIA_DIRECTIVE_RE.sub(replace, body)
    return body_with_markers, media_blocks


def replace_icon_markup(markup: str) -> str:
    icons = {
        "fa-file-pdf-o": '<svg class="inline-icon inline-icon-svg inline-icon-pdf" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 2.75h8.2L19 7.55V21.25H6A2.25 2.25 0 0 1 3.75 19V5A2.25 2.25 0 0 1 6 2.75Zm7.5 1.8v4h4M8 12.25h6.5M8 15.75h8M8 8.75h2.5"/></svg>',
        "fa-github": '<svg class="inline-icon inline-icon-svg inline-icon-github" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2.17c-3.22.7-3.9-1.36-3.9-1.36-.52-1.34-1.28-1.7-1.28-1.7-1.05-.72.08-.71.08-.71 1.16.08 1.77 1.2 1.77 1.2 1.03 1.76 2.7 1.25 3.36.96.1-.75.4-1.25.73-1.54-2.57-.29-5.27-1.29-5.27-5.73 0-1.27.45-2.3 1.2-3.11-.12-.3-.52-1.47.11-3.06 0 0 .98-.31 3.16 1.19A10.92 10.92 0 0 1 12 5.95c.99 0 1.98.13 2.91.38 2.18-1.5 3.16-1.19 3.16-1.19.63 1.59.23 2.76.11 3.06.75.81 1.2 1.84 1.2 3.11 0 4.45-2.71 5.43-5.29 5.72.42.36.78 1.08.78 2.18v3.24c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z"/></svg>',
        "fa-youtube": '<span class="inline-icon inline-icon-youtube" aria-hidden="true">▶</span>',
        "fa-youtube-play": '<span class="inline-icon inline-icon-youtube" aria-hidden="true">▶</span>',
        "fa-chart-bar": '<svg class="inline-icon inline-icon-svg inline-icon-results" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 20V10M12 20V4M19 20v-7"/></svg>',
        "fa-results": '<span class="inline-icon inline-icon-results" aria-hidden="true">↘</span>',
    }

    def replace(match: re.Match[str]) -> str:
        return icons.get(match.group(1), "")

    return re.sub(r'<i\s+class="fa\s+([^" ]+)"[^>]*>\s*</i>', replace, markup)


def render_container(markdown: MarkdownIt, name: str, content: str) -> str:
    name = name.lower()
    if name == "dark-mode" and not content.strip():
        return '<div class="dark-mode-control"><label><input type="checkbox" data-dark-mode> Dark mode</label></div>'

    if name == "row":
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        items: list[str] = []
        current: list[str] = []
        for line in lines:
            is_media = line.startswith("@[") or line.startswith("![")
            if is_media:
                if current:
                    items.append("\n".join(current))
                current = [line]
            elif current:
                current.append(line)
            else:
                items.append(line)
        if current:
            items.append("\n".join(current))
        inner = "\n".join(
            f'<div class="column media-column">{render_row_item(markdown, item)}</div>'
            for item in items
        )
        return f'<div class="columns is-centered is-multiline media-row">\n{inner}\n</div>'

    if name == "button":
        return render_button_links(content)

    inner = render_markdown(markdown, content.strip())
    inner = replace_icon_markup(inner)
    if name == "caption":
        return f'<div class="figure-caption content has-text-centered">\n{inner}\n</div>'
    if name == "author":
        return f'<div class="is-size-5 publication-authors">\n{inner}\n</div>'
    if name == "institution":
        return f'<div class="is-size-5 publication-authors">\n{inner}\n</div>'
    return f'<div class="markdown-container {html.escape(name, quote=True)}-container">\n{inner}\n</div>'


def polish_media_item(markup: str) -> str:
    markup = re.sub(
        r"(</video>\s*)<p>",
        r'\1<p class="media-caption">',
        markup,
        count=1,
    )
    markup = re.sub(
        r"(</p>\s*)<p>",
        r'\1<p class="media-caption">',
        markup,
        count=1,
    )
    return markup


def render_row_item(markdown: MarkdownIt, source: str) -> str:
    """Render one row item with its optional caption kept below the media."""
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    if not lines:
        return ""
    if lines[0].startswith("@[") or lines[0].startswith("!["):
        media_markup = render_markdown(markdown, lines[0])
        caption_markup = render_markdown(markdown, "\n".join(lines[1:])) if len(lines) > 1 else ""
        return polish_media_item(media_markup + caption_markup)
    return render_markdown(markdown, source)


def render_carousel(markdown: MarkdownIt, content: str) -> str:
    cells = CAROUSEL_CELL_RE.findall(content)
    if not cells:
        return render_markdown(markdown, content)
    rendered_cells = []
    for cell in cells:
        rendered = render_row_item(markdown, cell.strip())
        rendered_cells.append(f'<div class="item">{rendered}</div>')
    return (
        '<div id="results-carousel" class="carousel results-carousel">'
        + "".join(rendered_cells)
        + "</div>"
    )


def render_markdown(markdown: MarkdownIt, body: str) -> str:
    containers: list[str] = []
    carousels: list[str] = []
    inline_icons: list[str] = []

    def replace_icon(match: re.Match[str]) -> str:
        inline_icons.append(replace_icon_markup(f'<i class="fa {match.group(1)}"></i>'))
        return f"INLINEICON{len(inline_icons) - 1}TOKEN"

    def replace_container(match: re.Match[str]) -> str:
        index = len(containers)
        containers.append(render_container(markdown, match.group(1), match.group(2)))
        return f"\n\n<!-- CONTAINER_{index} -->\n\n"

    def replace_carousel(match: re.Match[str]) -> str:
        index = len(carousels)
        carousels.append(render_carousel(markdown, match.group(1)))
        return f"\n\n<!-- CAROUSEL_{index} -->\n\n"

    # Extract carousels first so their carousel-cell containers are not consumed
    # by the generic three-colon container parser.
    body_with_carousels = CAROUSEL_RE.sub(replace_carousel, body)
    body_with_containers = CONTAINER_RE.sub(replace_container, body_with_carousels)
    body_with_containers = ICON_TAG_RE.sub(replace_icon, body_with_containers)
    body_with_containers = SUPERSCRIPT_RE.sub(r"<sup>\1</sup>", body_with_containers)
    body_with_media, media_blocks = replace_media_directives(markdown, body_with_containers)
    rendered = replace_video_paragraphs(markdown.render(body_with_media))
    for index, block in enumerate(media_blocks):
        rendered = rendered.replace(f"<!-- MEDIA_DIRECTIVE_{index} -->", block)
    for index, container in enumerate(containers):
        rendered = rendered.replace(f"<!-- CONTAINER_{index} -->", container)
    for index, carousel in enumerate(carousels):
        rendered = rendered.replace(f"<!-- CAROUSEL_{index} -->", carousel)
    for index, icon in enumerate(inline_icons):
        rendered = rendered.replace(f"INLINEICON{index}TOKEN", icon)
    return rendered


def make_action_buttons(metadata: dict[str, str]) -> str:
    icons = {
        "paper": '<svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 2.75h8.2L19 7.55V21.25H6A2.25 2.25 0 0 1 3.75 19V5A2.25 2.25 0 0 1 6 2.75Zm7.5 1.8v4h4M8 12.25h6.5M8 15.75h8M8 8.75h2.5"/></svg>',
        "demo": '<svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m9.25 6.9 8 5.1-8 5.1V6.9Z"/></svg>',
        "github": '<svg class="button-icon button-icon-github" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2.17c-3.22.7-3.9-1.36-3.9-1.36-.52-1.34-1.28-1.7-1.28-1.7-1.05-.72.08-.71.08-.71 1.16.08 1.77 1.2 1.77 1.2 1.03 1.76 2.7 1.25 3.36.96.1-.75.4-1.25.73-1.54-2.57-.29-5.27-1.29-5.27-5.73 0-1.27.45-2.3 1.2-3.11-.12-.3-.52-1.47.11-3.06 0 0 .98-.31 3.16 1.19A10.92 10.92 0 0 1 12 5.95c.99 0 1.98.13 2.91.38 2.18-1.5 3.16-1.19 3.16-1.19.63 1.59.23 2.76.11 3.06.75.81 1.2 1.84 1.2 3.11 0 4.45-2.71 5.43-5.29 5.72.42.36.78 1.08.78 2.18v3.24c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z"/></svg>',
        "huggingface": '<span class="button-icon button-icon-huggingface" aria-hidden="true">🤗</span>',
    }
    links = [
        ("paper", metadata.get("paper", ""), "Paper", "button-paper"),
        ("demo", metadata.get("demo", ""), "Demo", "button-demo"),
        ("github", metadata.get("github", metadata.get("code", "")), "GitHub", "button-github"),
        ("huggingface", metadata.get("huggingface", ""), "Hugging Face", "button-huggingface"),
    ]
    buttons = []
    for icon_name, url, label, class_name in links:
        if not url:
            continue
        safe_url = html.escape(url, quote=True)
        external = ' target="_blank" rel="noopener noreferrer"' if url.startswith(("http://", "https://")) else ""
        buttons.append(f'<a class="button button-pill {class_name}" href="{safe_url}"{external} title="{label}">{icons[icon_name]}<span>{label}</span></a>')
    buttons.extend([
        '<a class="button button-pill button-results" href="#results" title="View results"><span class="button-icon button-icon-results" aria-hidden="true">↘</span><span>Results</span></a>',
        '<a class="button button-pill button-citation" href="#citation" title="View citation"><span class="button-icon button-icon-citation" aria-hidden="true">{ }</span><span>Citation</span></a>',
    ])
    return "\n      ".join(buttons)


def main() -> None:
    metadata, body = parse_project(ROOT / "project.md")
    markdown = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
    markdown.enable("table").enable("strikethrough")
    nav_match = NAV_CONTAINER_RE.search(body)
    navigation = render_navigation(markdown, nav_match.group(1)) if nav_match else ""
    if nav_match:
        body = body[: nav_match.start()] + body[nav_match.end() :]
    button_match = re.search(r"^::: button\n(.*?)^:::\s*$", body, re.MULTILINE | re.DOTALL)
    button_source = button_match.group(1).strip() if button_match else ""
    rendered = make_sections(add_heading_ids(render_markdown(markdown, body)), button_source)

    title_match = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    markdown_title = title_match.group(1).strip() if title_match else "Research Project"
    short_title = markdown_title.split(":", 1)[0]

    values = {
        "title": metadata.get("title", short_title),
        "description": metadata.get("tagline", markdown_title),
        "navigation": navigation,
        "sections": rendered,
    }
    values.update(metadata)
    template = (ROOT / "template.html").read_text(encoding="utf-8")
    for key, value in values.items():
        raw_keys = {"navigation", "sections"}
        replacement = value if key in raw_keys else html.escape(value, quote=True)
        template = template.replace("{{" + key + "}}", replacement)
    (ROOT / "index.html").write_text(template, encoding="utf-8")
    print("Built index.html from project.md")


if __name__ == "__main__":
    main()
