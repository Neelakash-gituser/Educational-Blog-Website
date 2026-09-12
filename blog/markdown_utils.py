"""Markdown rendering for posts and comments.

Posts are written by trusted authors but are still sanitised: a single
compromised author account should not be able to inject scripts into every
reader's browser.  Comments are rendered with a much smaller feature set.
"""

from __future__ import annotations

import re

import bleach
import markdown
from django.utils.safestring import mark_safe

# Post extensions: fenced code with Pygments highlighting, tables, footnotes,
# task lists, admonitions, a table of contents and typographic niceties.
POST_EXTENSIONS = [
    "extra",
    "admonition",
    "sane_lists",
    "smarty",
    "toc",
    "pymdownx.superfences",
    "pymdownx.highlight",
    "pymdownx.inlinehilite",
    "pymdownx.tasklist",
    "pymdownx.tilde",
    "pymdownx.caret",
    "pymdownx.smartsymbols",
    "pymdownx.magiclink",
    "pymdownx.arithmatex",
]

POST_EXTENSION_CONFIGS = {
    "pymdownx.highlight": {
        "css_class": "codehilite",
        "guess_lang": False,
        "linenums": False,
        "anchor_linenums": False,
        "use_pygments": True,
        "pygments_style": "default",
        "noclasses": False,
        # Keeps a language-<name> class on the block so the copy widget can
        # label it without re-parsing the source.
        "pygments_lang_class": True,
    },
    "pymdownx.tasklist": {"custom_checkbox": True},
    "toc": {"permalink": "¶", "permalink_class": "heading-anchor", "toc_depth": "2-4"},
    "pymdownx.magiclink": {"repo_url_shorthand": True},
    # generic mode emits \(...\) / \[...\] for MathJax instead of <script> tags,
    # which survives HTML sanitising.
    "pymdownx.arithmatex": {"generic": True},
}

COMMENT_EXTENSIONS = [
    "fenced_code",
    "pymdownx.arithmatex",
    "pymdownx.magiclink",
    "tables",
    "nl2br",
    "sane_lists",
    "pymdownx.superfences",
    "pymdownx.highlight",
]

COMMENT_EXTENSION_CONFIGS = {
    "pymdownx.highlight": {
        "css_class": "codehilite",
        "guess_lang": False,
        "use_pygments": True,
        "pygments_lang_class": True,
    },
    "pymdownx.arithmatex": {"generic": True},
}

ALLOWED_TAGS = {
    "a", "abbr", "acronym", "b", "blockquote", "br", "caption", "code", "col",
    "colgroup", "dd", "del", "details", "div", "dl", "dt", "em", "figcaption",
    "figure", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "input",
    "ins", "kbd", "li", "mark", "ol", "p", "pre", "q", "s", "samp", "section",
    "small", "span", "strong", "sub", "summary", "sup", "table", "tbody", "td",
    "tfoot", "th", "thead", "tr", "ul", "var",
}

ALLOWED_ATTRIBUTES = {
    "*": ["class", "id", "title", "dir"],
    "a": ["href", "title", "rel", "target", "class", "id"],
    "img": ["src", "alt", "title", "width", "height", "loading", "class"],
    "input": ["type", "checked", "disabled", "class"],
    "td": ["colspan", "rowspan", "align"],
    "th": ["colspan", "rowspan", "align", "scope"],
    "ol": ["start", "type", "class"],
    "details": ["open"],
    "span": ["class"],
    "div": ["class"],
    "code": ["class"],
    "pre": ["class"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

# ``style`` is deliberately absent from ALLOWED_ATTRIBUTES, so inline CSS is
# stripped outright rather than sanitised property by property.

COMMENT_ALLOWED_TAGS = {
    "a", "b", "blockquote", "br", "code", "del", "em", "i", "kbd", "li", "ol",
    "p", "pre", "span", "strong", "table", "tbody", "td", "th", "thead", "tr",
    "ul", "div",
}


# bleach keeps the *text* inside a tag it strips, so `<script>steal()</script>`
# would survive as visible prose. Remove those blocks wholesale first. Code
# fences are already HTML-escaped by this point, so real code is untouched.
_SCRIPTISH_RE = re.compile(
    r"<\s*(script|style|iframe|object|embed|template)\b[^>]*>.*?<\s*/\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)


def _clean(html: str, tags: set[str]) -> str:
    html = _SCRIPTISH_RE.sub("", html)
    return bleach.clean(
        html,
        tags=tags,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )


def render_markdown(text: str) -> str:
    """Render a post body to sanitised HTML."""
    if not text:
        return ""
    md = markdown.Markdown(
        extensions=POST_EXTENSIONS,
        extension_configs=POST_EXTENSION_CONFIGS,
        output_format="html",
    )
    # magiclink (above) turns bare URLs into links; bleach.linkify is not used
    # because it double-escapes entities inside the code blocks it skips.
    return _clean(md.convert(text), ALLOWED_TAGS)


def render_comment(text: str) -> str:
    """Render a comment to sanitised HTML with a reduced feature set."""
    if not text:
        return ""
    md = markdown.Markdown(
        extensions=COMMENT_EXTENSIONS,
        extension_configs=COMMENT_EXTENSION_CONFIGS,
        output_format="html",
    )
    return _clean(md.convert(text), COMMENT_ALLOWED_TAGS)


def render_toc(text: str) -> str:
    """Return just the table of contents for a post body."""
    if not text:
        return ""
    md = markdown.Markdown(
        extensions=POST_EXTENSIONS, extension_configs=POST_EXTENSION_CONFIGS
    )
    md.convert(text)
    toc = getattr(md, "toc", "")
    # A single-item list is noise, not navigation.
    return toc if toc.count("<li>") > 1 else ""


_TAG_RE = re.compile(r"<[^>]+>")
_WORD_RE = re.compile(r"[\w'’-]+")


def strip_markdown(text: str, limit: int | None = None) -> str:
    """Plain-text version of a markdown body, for excerpts and meta tags."""
    if not text:
        return ""
    html = markdown.markdown(text, extensions=["extra"])
    plain = bleach.clean(_TAG_RE.sub(" ", html), tags=set(), strip=True)
    plain = re.sub(r"\s+", " ", plain).strip()
    if limit and len(plain) > limit:
        plain = plain[:limit].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
    return plain


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(strip_markdown(text)))


def reading_time(text: str, wpm: int = 220) -> int:
    """Estimated reading time in whole minutes (never zero)."""
    return max(1, round(word_count(text) / wpm))


def safe(html: str):
    return mark_safe(html)  # noqa: S308 - callers pass already-sanitised HTML
