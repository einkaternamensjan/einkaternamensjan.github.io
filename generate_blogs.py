import re
import json
from pathlib import Path

ROOT = Path(__file__).parent
BLOGS_DIR = ROOT / "blogs"
TEMPLATE_FILE = ROOT / "blog_template.html"
OUT_FILE = ROOT / "blogs.html"
POSTS_DIR = ROOT / "posts"

if not BLOGS_DIR.exists():
    print(f"blogs folder not found: {BLOGS_DIR}")
    raise SystemExit(1)

if not POSTS_DIR.exists():
    POSTS_DIR.mkdir(parents=True, exist_ok=True)

blog_paths = [
    p.name
    for p in BLOGS_DIR.iterdir()
    if p.suffix == ".md" and not p.name.startswith("_")
]

blog_paths = list(reversed(blog_paths))


def title_from_filename(blog_path):
    title = blog_path.replace('.md', '')
    title = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', title)
    title = title.replace('-', ' ')
    return title.title()


def title_from_markdown(raw):
    for line in raw.splitlines():
        clean = line.strip()
        if not clean or (clean.startswith('<!--') and clean.endswith('-->')):
            continue
        m = re.match(r'^(#{1,6})\s*(.+)$', clean)
        if m:
            return m.group(2).strip()
        break
    return None


def strip_first_markdown_title(raw):
    lines = raw.splitlines()
    i = 0
    # skip leading whitespace and comments
    while i < len(lines):
        line = lines[i].strip()
        if not line or (line.startswith('<!--') and line.endswith('-->')):
            i += 1
            continue
        break

    if i >= len(lines):
        return raw

    if re.match(r'^(#{1,6})\s*.+$', lines[i].strip()):
        return '\n'.join(lines[:i] + lines[i+1:])
    return raw


def pair_id_from_markdown(raw):
    m = re.search(r'<!--\s*pair\s*:\s*([a-zA-Z0-9_-]+)\s*-->', raw, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


def create_slug(filename):
    slug = filename.replace('.md', '')
    slug = re.sub(r'[^a-z0-9]+', '-', slug.lower())
    slug = slug.strip('-')
    if slug and slug[0].isdigit():
        slug = 'post-' + slug
    return slug


def guess_language(text):
    sample = text.lower()
    german_indicators = ['ä', 'ö', 'ü', 'ß', ' und ', ' der ', ' die ', ' das ', ' nicht ', ' ist ', ' ich ', ' sie ', ' mit ', ' für ', 'sein ', 'sich ']
    for token in german_indicators:
        if token in sample:
            return 'de'
    return 'en'


def compile_markdown(markdown: str):
    out = markdown
    out = out.replace('\\_', '_')
    out = out.replace('\r\n', '\n').replace('\r', '\n')

    out = re.sub(r'### (.+?)\n', r'<h4>\1</h4>\n', out)
    out = re.sub(r'## (.+?)\n', r'<h3>\1</h3>\n', out)
    out = re.sub(r'https://([^\s<]+)(\s)', r"<a href='https://\1'>https://\1</a>\2", out)
    out = re.sub(r'```hs\n(.*?)```', lambda m: f"<pre><code class='language-haskell'>{m.group(1)}</code></pre>", out, flags=re.DOTALL)
    out = re.sub(r'```(.*?)```', lambda m: f"<pre><code>{m.group(1)}</code></pre>", out, flags=re.DOTALL)
    out = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', out)
    out = re.sub(r'\*(.+?)\*', r'<em>\1</em>', out)

    segments = []
    for block in re.split(r'\n\s*\n', out):
        block = block.strip()
        if not block:
            continue

        if block.startswith('<h3>') or block.startswith('<h4>') or block.startswith('<pre>'):
            if not block.startswith('<pre>'):
                block = block.replace('\n', '<br>')
            segments.append(block)
        else:
            block = block.replace('\n', '<br>')
            segments.append(f'<p>{block}</p>')

    return '\n'.join(segments)


blogs_data = []
for blog_path in blog_paths:
    path = BLOGS_DIR / blog_path
    with path.open('r', encoding='utf-8', errors='replace') as fh:
        raw = fh.read()

    footnotes = []
    for m in re.finditer(r'^\[\^(\d+)\]:\s*(.+)$', raw, flags=re.MULTILINE):
        footnotes.append({'number': int(m.group(1)), 'text': m.group(2).strip()})

    raw_without_footnotes = re.sub(r'^\[\^\d+\]:.*(?:\n|$)', '', raw, flags=re.MULTILINE)

    title = title_from_markdown(raw_without_footnotes) or title_from_filename(blog_path)
    slug = create_slug(blog_path)

    markdown_body = strip_first_markdown_title(raw_without_footnotes)

    date_match = re.match(r'^(\d{4}-\d{2}-\d{2})-', blog_path)
    date = date_match.group(1) if date_match else 'undated'

    lang = guess_language(raw_without_footnotes)
    pair_id = pair_id_from_markdown(raw_without_footnotes)
    group_id = f"{date}-{pair_id}" if pair_id else slug

    blogs_data.append({
        'name': blog_path,
        'date': date,
        'title': title,
        'slug': slug,
        'group_id': group_id,
        'raw': raw_without_footnotes,
        'compiled': compile_markdown(markdown_body),
        'footnotes': footnotes,
        'lang': lang,
    })

if not TEMPLATE_FILE.exists():
    print(f"Template not found: {TEMPLATE_FILE}")
    raise SystemExit(1)

with TEMPLATE_FILE.open('r', encoding='utf-8', errors='replace') as fh:
    template = fh.read()


posts_by_group = {}
for entry in blogs_data:
    posts_by_group.setdefault(entry['group_id'], []).append(entry)

for group_id, entries in posts_by_group.items():
    first_entry = entries[0]
    group_slug = create_slug(group_id)
    date = first_entry['date']

    group_nav_items = []
    group_articles = []

    for entry in entries:
        entry_anchor = f"#{entry['slug']}"
        group_nav_items.append(f"<a href='{entry_anchor}'>- {entry['lang'].upper()}: {entry['title']}</a>")

        script_block = ''
        if entry.get('footnotes'):
            calls = []
            for fn in entry['footnotes']:
                text_js = json.dumps(fn['text'])
                calls.append(f"  window.addFootnote('{entry['slug']}', {fn['number']}, {text_js});")
            script_block = '<script>document.addEventListener(\'DOMContentLoaded\', function() {\n' + '\n'.join(calls) + '\n});</script>'

        article_html = (
            f"<article id='{entry['slug']}' class='bilingual-column lang-{entry['lang']}'>"
            f"<h2>{'Deutsch' if entry['lang'] == 'de' else 'English'}</h2>"
            f"<h1 class='post-title'>{entry['title']}</h1>"
            f"{entry['compiled']}"
            f"{script_block}"
            f"</article>"
        )

        group_articles.append(article_html)

    chapter_links = ''.join([
        f"<span class='lang-chip'><a href='#{entry['slug']}'>- {entry['lang'].upper()}</a></span>"
        for entry in entries
    ])

    de_entry = next((e for e in entries if e['lang'] == 'de'), None)
    en_entry = next((e for e in entries if e['lang'] == 'en'), None)

    if de_entry and en_entry:
        title_html = (
            f"<h1 class='title-de'>Deutsch: {de_entry['title']}</h1>"
            f"<h1 class='title-en'>English: {en_entry['title']}</h1>"
        )
    elif de_entry:
        title_html = f"<h1 class='title-de'>Deutsch: {de_entry['title']}</h1>"
    elif en_entry:
        title_html = f"<h1 class='title-en'>English: {en_entry['title']}</h1>"
    else:
        title_html = f"<h1>{first_entry['title']}</h1>"

    # Format date as DD.MM.YY
    date_parts = date.split('-')
    formatted_date = f"{date_parts[2]}.{date_parts[1]}.{date_parts[0][2:]}"

    group_content = (
        f"<div class='group-header'>{title_html}</div>"
        f"<nav aria-label='Post languages'>{chapter_links}</nav>"
        f"<div class='bilingual-layout'>{''.join(group_articles)}</div>"
    )

    group_index_html = '<br>'.join(group_nav_items)
    page_html = template.replace('###STYLESHEET###', '../styles.css').replace('###BLOG-CONTENTS###', group_index_html).replace('###BLOGS###', group_content).replace('###PUBLICATION-DATE###', f'Published on {formatted_date}')
    page_html = page_html.replace('<body>', '<body class="bilingual-mode">')

    target_file = POSTS_DIR / f"{group_slug}.html"
    with target_file.open('w', encoding='utf-8', errors='replace') as fh:
        fh.write(page_html)

    print(f"Wrote {target_file} with {len(entries)} language versions.")

index_items = []
for group_id, entries in posts_by_group.items():
    first_entry = entries[0]
    group_slug = create_slug(group_id)
    lang_labels = ', '.join(sorted({entry['lang'] for entry in entries}))

    de_entry = next((e for e in entries if e['lang'] == 'de'), None)
    en_entry = next((e for e in entries if e['lang'] == 'en'), None)
    title_parts = []
    if de_entry:
        title_parts.append(f"{de_entry['title']}")
    if en_entry:
        title_parts.append(f"{en_entry['title']}")
    if not title_parts:
        title_parts.append(first_entry['title'])

    composed_title = ' / '.join(title_parts)

    # Format date as DD.MM.YY using this entry's own date
    date_parts = first_entry['date'].split('-')
    formatted_date = f"{date_parts[2]}.{date_parts[1]}.{date_parts[0][2:]}"

    index_items.append(f"<li><a href='posts/{group_slug}.html'>{composed_title} ({lang_labels}) - {formatted_date}</a></li>")

index_content = (
    '<header><h1>Blog Index</h1></header>'
    f"<main><ul class='post-index'>{''.join(index_items)}</ul></main>"
)

index_html = template.replace('###STYLESHEET###', 'styles.css').replace('###BLOG-CONTENTS###', '').replace('###BLOGS###', index_content).replace('###PUBLICATION-DATE###', '')
with OUT_FILE.open('w', encoding='utf-8', errors='replace') as fh:
    fh.write(index_html)

print(f"Wrote {OUT_FILE} with {len(posts_by_group)} groups.")
