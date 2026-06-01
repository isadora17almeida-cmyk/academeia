from __future__ import annotations

import re
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


def _inline(text: str) -> str:
    text = escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return text


@register.filter(name='simple_markdown')
def simple_markdown(value: str) -> str:
    """Renderiza markdown básico sem dependências externas.

    Suporta títulos (#, ##, ###), listas com '- ' e negrito com **texto**.
    O restante é escapado antes de ser marcado como seguro.
    """
    if not value:
        return ''

    html: list[str] = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            html.append('</ul>')
            in_list = False

    for raw_line in str(value).splitlines():
        line = raw_line.strip()
        if not line:
            close_list()
            continue
        if line.startswith('### '):
            close_list()
            html.append(f'<h3>{_inline(line[4:])}</h3>')
        elif line.startswith('## '):
            close_list()
            html.append(f'<h2>{_inline(line[3:])}</h2>')
        elif line.startswith('# '):
            close_list()
            html.append(f'<h1>{_inline(line[2:])}</h1>')
        elif line.startswith('- '):
            if not in_list:
                html.append('<ul>')
                in_list = True
            html.append(f'<li>{_inline(line[2:])}</li>')
        else:
            close_list()
            html.append(f'<p>{_inline(line)}</p>')

    close_list()
    return mark_safe('\n'.join(html))
