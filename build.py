#!/usr/bin/env python3
"""Build index.html from project.md and the local HTML template."""

from __future__ import annotations

import html
import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse, urlunparse

try:
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
SUPERSCRIPT_RE = re.compile(r"\^([0-9]+(?:,[*†‡]+)?|[*†‡]+)\^")
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
NAV_CONTAINER_RE = re.compile(
    r"^:::\s*nav\s*$\n(.*?)^:::\s*$",
    re.MULTILINE | re.DOTALL,
)


def slugify(text: str) -> str:
    plain = re.sub(r"<[^>]+>", "", text)
    plain = html.unescape(plain).strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", plain).strip("-")
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


def make_sections(markup: str) -> str:
    parts = re.split(r"(?=<h2(?:\s|>))", markup)
    sections: list[str] = []

    hero = parts[0].strip()
    if hero:
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
    if name == "caption":
        return f'<div class="figure-caption content has-text-centered">\n{inner}\n</div>'
    if name == "author":
        return f'<div class="is-size-5 publication-authors">\n{inner}\n</div>'
    if name == "institution":
        return f'<div class="is-size-5 publication-authors">\n{inner}\n</div>'
    if name == "contribution":
        return f'<div class="publication-contributions">\n{inner}\n</div>'
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
    body_with_containers = SUPERSCRIPT_RE.sub(r"<sup>\1</sup>", body_with_containers)
    body_with_media, media_blocks = replace_media_directives(markdown, body_with_containers)
    rendered = markdown.render(body_with_media)
    for index, block in enumerate(media_blocks):
        rendered = rendered.replace(f"<!-- MEDIA_DIRECTIVE_{index} -->", block)
    for index, container in enumerate(containers):
        rendered = rendered.replace(f"<!-- CONTAINER_{index} -->", container)
    for index, carousel in enumerate(carousels):
        rendered = rendered.replace(f"<!-- CAROUSEL_{index} -->", carousel)
    return rendered


def main() -> None:
    body = (ROOT / "project.md").read_text(encoding="utf-8")
    markdown = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
    markdown.enable("table").enable("strikethrough")
    nav_match = NAV_CONTAINER_RE.search(body)
    navigation = render_navigation(markdown, nav_match.group(1)) if nav_match else ""
    if nav_match:
        body = body[: nav_match.start()] + body[nav_match.end() :]
    rendered = make_sections(render_markdown(markdown, body))

    title_match = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    markdown_title = title_match.group(1).strip() if title_match else "Research Project"
    short_title = markdown_title.split(":", 1)[0]

    values = {
        "title": short_title,
        "description": markdown_title,
        "navigation": navigation,
        "sections": rendered,
    }
    template = (ROOT / "template.html").read_text(encoding="utf-8")
    for key, value in values.items():
        raw_keys = {"navigation", "sections"}
        replacement = value if key in raw_keys else html.escape(value, quote=True)
        template = template.replace("{{" + key + "}}", replacement)
    (ROOT / "index.html").write_text(template, encoding="utf-8")
    print("Built index.html from project.md")


if __name__ == "__main__":
    main()
