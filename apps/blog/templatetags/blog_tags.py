"""
Custom template tags and filters for the blog app.
"""
import re
import bleach
from django import template
from django.db.models import Count, Q
from django.utils.html import escape
from django.utils.safestring import mark_safe
from markdownx.utils import markdownify as _markdownify

from apps.blog.models import Post

register = template.Library()

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'b', 'i', 'u', 's', 'del',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    'a', 'img',
    'blockquote', 'pre', 'code',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'hr', 'div', 'span',
]

ALLOWED_ATTRIBUTES = {
    'a':   ['href', 'title', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'code': ['class'],
    'pre':  ['class'],
    'span': ['class'],
    'div':  ['class'],
    'th':   ['scope'],
    'td':   ['colspan', 'rowspan'],
}


@register.filter(name='markdownify', is_safe=True)
def markdownify(value):
    """
    Convert Markdown text to sanitized HTML.
    Usage: {{ post.body|markdownify }}
    """
    if not value:
        return ''
    html = _markdownify(value)
    clean_html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=False,
    )
    return mark_safe(clean_html)


@register.simple_tag
def render_toc(body):
    """Extract H2/H3 headings from Markdown and render as navigation ToC."""
    headings = re.findall(r'^(#{2,3})\s+(.+)$', body, re.MULTILINE)
    if len(headings) < 3:
        return ''

    items = []
    for hashes, text in headings:
        level = len(hashes)
        anchor = re.sub(r'[^\w\s-]', '', text.lower()).strip()
        anchor = re.sub(r'[\s_]+', '-', anchor)
        indent = 'toc-h3' if level == 3 else 'toc-h2'
        items.append(
            f'<li class="{indent}"><a href="#{anchor}" class="toc-link">{escape(text)}</a></li>'
        )

    html = (
        '<nav class="toc-nav" aria-label="Spis treści">'
        '<ul class="toc-list">'
        + ''.join(items)
        + '</ul></nav>'
    )
    return mark_safe(html)



@register.inclusion_tag('partials/widget_recent_posts.html')
def show_recent_posts(count=5):
    """Renders the N most recently published posts."""
    recent = Post.published.order_by('-publish')[:count]
    return {'recent_posts': recent}


@register.inclusion_tag('partials/widget_most_commented.html')
def show_most_commented(count=5):
    """Renders the N posts with the highest number of active comments."""
    posts = (
        Post.published
        .annotate(comment_count=Count('comments', filter=Q(comments__active=True)))
        .order_by('-comment_count')[:count]
    )
    return {'most_commented': posts}


@register.inclusion_tag('partials/widget_tag_cloud.html')
def show_tag_cloud():
    """Renders a tag cloud using taggit tags sorted by usage count."""
    from taggit.models import Tag
    tags = (
        Tag.objects
        .annotate(post_count=Count('taggit_taggeditem_items'))
        .filter(post_count__gt=0)
        .order_by('-post_count')[:30]
    )
    return {'tags': tags}



@register.filter(name='reading_bar')
def reading_bar(minutes):
    """Returns an ASCII progress bar for reading time.

    Usage: {{ post.reading_time|reading_bar }}
    Example: {{ 3|reading_bar }} → ███░░░░░░░
    """
    total = 10
    try:
        filled = min(int(minutes), total)
    except (TypeError, ValueError):
        filled = 0
    return '█' * filled + '░' * (total - filled)
