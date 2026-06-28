import re
import json
from pathlib import Path

ROOT = Path(__file__).parent
BLOGS_DIR = ROOT / "blogs"
BIBLIO_DIR = ROOT / "bibliography"
TEMPLATE_FILE = ROOT / "blog_template.html"
OUT_FILE = ROOT / "blogs.html"
BIBLIO_OUT_FILE = ROOT / "bibliography.html"
POSTS_DIR = ROOT / "posts"
BIBLIO_POSTS_DIR = ROOT / "bibliography_posts"

if not BLOGS_DIR.exists():
    print(f"blogs folder not found: {BLOGS_DIR}")
    raise SystemExit(1)

BIBLIO_DIR.mkdir(parents=True, exist_ok=True)
POSTS_DIR.mkdir(parents=True, exist_ok=True)
BIBLIO_POSTS_DIR.mkdir(parents=True, exist_ok=True)


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
    m = re.search(r'<!--\s*pair\s*:\s*([\w-]+)\s*-->', raw, flags=re.IGNORECASE | re.UNICODE)
    return m.group(1).strip() if m else None


def create_slug(filename):
    slug = filename.replace('.md', '')
    slug = re.sub(r'[^a-z0-9]+', '-', slug.lower())
    slug = slug.strip('-')
    if slug and slug[0].isdigit():
        slug = 'post-' + slug
    return slug


def load_markdown_entries(source_dir):
    markdown_paths = [
        p.name
        for p in source_dir.iterdir()
        if p.suffix == ".md" and not p.name.startswith("_")
    ]
    markdown_paths = list(reversed(markdown_paths))

    entries = []
    for filename in markdown_paths:
        path = source_dir / filename
        with path.open('r', encoding='utf-8', errors='replace') as fh:
            raw = fh.read()

        footnotes = []
        for m in re.finditer(r'^\[\^(\d+)\]:\s*(.+)$', raw, flags=re.MULTILINE):
            footnotes.append({'number': int(m.group(1)), 'text': m.group(2).strip()})

        raw_without_footnotes = re.sub(r'^\[\^\d+\]:.*(?:\n|$)', '', raw, flags=re.MULTILINE)

        title = title_from_markdown(raw_without_footnotes) or title_from_filename(filename)
        slug = create_slug(filename)
        markdown_body = strip_first_markdown_title(raw_without_footnotes)
        date = parse_date_from_filename(filename) or 'undated'
        lang = guess_language(raw_without_footnotes)
        pair_id = pair_id_from_markdown(raw_without_footnotes)
        group_id = f"{date}-{pair_id}" if pair_id else slug

        entries.append({
            'name': filename,
            'date': date,
            'title': title,
            'slug': slug,
            'group_id': group_id,
            'raw': raw_without_footnotes,
            'compiled': compile_markdown(markdown_body),
            'footnotes': footnotes,
            'lang': lang,
        })

    return entries


def parse_date_from_filename(filename):
    match = re.match(r'^(\d{4}-\d{2}-\d{2})-', filename)
    if match:
        return match.group(1)
    match = re.match(r'^(\d{2}-\d{2}-\d{4})-', filename)
    if match:
        day, month, year = match.group(1).split('-')
        return f"{year}-{month}-{day}"
    return None


def format_date(date):
    if not date:
        return 'undated'
    parts = date.split('-')
    if len(parts) == 3:
        year, month, day = parts
        if len(year) == 4 and len(month) == 2 and len(day) == 2:
            return f"{day}.{month}.{year[2:]}"
    return date


def guess_language(text):
    sample = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL).lower()
    german_words = ['ä', 'ö', 'ü', 'ß', ' und ', ' der ', ' die ', ' das ', ' nicht ', ' ist ', ' ich ', ' sie ', ' mit ', ' für ', 'sein ', 'sich ']
    english_words = [' the ', ' and ', ' is ', ' in ', ' to ', ' of ', ' that ', ' it ', ' for ', ' on ', ' with ', ' as ', ' was ', ' at ', ' be ']

    german_score = 0
    english_score = 0

    # strong indicator: German special characters
    for ch in ['ä', 'ö', 'ü', 'ß']:
        if ch in sample:
            german_score += 5

    for w in german_words:
        german_score += sample.count(w)
    for w in english_words:
        english_score += sample.count(w)

    return 'de' if german_score > english_score else 'en'


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


blogs_data = load_markdown_entries(BLOGS_DIR)
bibliography_data = load_markdown_entries(BIBLIO_DIR)

if not TEMPLATE_FILE.exists():
    print(f"Template not found: {TEMPLATE_FILE}")
    raise SystemExit(1)

with TEMPLATE_FILE.open('r', encoding='utf-8', errors='replace') as fh:
    template = fh.read()


def generate_collection(entries, output_file, page_title, post_folder, root_stylesheet, group_stylesheet, root_back_href, group_back_href, render_single_page=False):
    posts_by_group = {}
    for entry in entries:
        posts_by_group.setdefault(entry['group_id'], []).append(entry)

    groups_html = []
    for group_id, group_entries in posts_by_group.items():
        first_entry = group_entries[0]
        group_slug = create_slug(group_id)
        date = first_entry['date']

        group_nav_items = []
        group_articles = []

        for entry in group_entries:
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
            for entry in group_entries
        ])

        de_entry = next((e for e in group_entries if e['lang'] == 'de'), None)
        en_entry = next((e for e in group_entries if e['lang'] == 'en'), None)

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

        formatted_date = format_date(date)
        group_content = (
            f"<div class='group-header'>{title_html}</div>"
            f"<nav aria-label='Post languages'>{chapter_links}</nav>"
            f"<div class='bilingual-layout'>{''.join(group_articles)}</div>"
        )

        if render_single_page:
            groups_html.append(group_content)

        group_index_html = '<br>'.join(group_nav_items)
        page_html = template.replace('###PAGE-TITLE###', page_title)
        page_html = page_html.replace('###STYLESHEET###', group_stylesheet)
        page_html = page_html.replace('###BACK-HOME-HREF###', group_back_href)
        page_html = page_html.replace('###BLOG-CONTENTS###', group_index_html)
        page_html = page_html.replace('###BLOGS###', group_content)
        page_html = page_html.replace('###PUBLICATION-DATE###', f'Published on {formatted_date}')
        page_html = page_html.replace('<body>', '<body class="bilingual-mode">')

        target_file = post_folder / f"{group_slug}.html"
        with target_file.open('w', encoding='utf-8', errors='replace') as fh:
            fh.write(page_html)

        print(f"Wrote {target_file} with {len(group_entries)} language versions.")

    index_items = []
    for group_id, group_entries in posts_by_group.items():
        first_entry = group_entries[0]
        group_slug = create_slug(group_id)
        lang_labels = ', '.join(sorted({entry['lang'] for entry in group_entries}))

        de_entry = next((e for e in group_entries if e['lang'] == 'de'), None)
        en_entry = next((e for e in group_entries if e['lang'] == 'en'), None)
        title_parts = []
        if de_entry:
            title_parts.append(f"{de_entry['title']}")
        if en_entry:
            title_parts.append(f"{en_entry['title']}")
        if not title_parts:
            title_parts.append(first_entry['title'])

        composed_title = ' / '.join(title_parts)
        formatted_date = format_date(first_entry['date'])
        index_items.append(f"<li><a href='{post_folder.name}/{group_slug}.html'>{composed_title} ({lang_labels}) - {formatted_date}</a></li>")

    if render_single_page:
        index_content = (
            f'<header><h1>{page_title}</h1></header>'
            + ''.join(groups_html)
        )
    else:
        index_content = (
            f'<header><h1>{page_title} Index</h1></header>'
            f"<main><ul class='post-index'>{''.join(index_items)}</ul></main>"
        )

    index_html = template.replace('###PAGE-TITLE###', page_title)
    index_html = index_html.replace('###STYLESHEET###', root_stylesheet)
    index_html = index_html.replace('###BACK-HOME-HREF###', root_back_href)
    index_html = index_html.replace('###BLOG-CONTENTS###', '')
    index_html = index_html.replace('###BLOGS###', index_content)
    index_html = index_html.replace('###PUBLICATION-DATE###', '')

    with output_file.open('w', encoding='utf-8', errors='replace') as fh:
        fh.write(index_html)

    print(f"Wrote {output_file} with {len(posts_by_group)} groups.")


generate_collection(blogs_data, OUT_FILE, 'Blog', POSTS_DIR, 'styles.css', '../styles.css', 'index.html', '../index.html')
generate_collection(bibliography_data, BIBLIO_OUT_FILE, 'Bibliography', BIBLIO_POSTS_DIR, 'styles.css', '../styles.css', 'index.html', '../index.html', render_single_page=True)
