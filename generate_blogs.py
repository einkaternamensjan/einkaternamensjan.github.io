# einkaternamensjan site files — set 9 (blog_template.html, generate_blogs.py, styles.css, post.js gehören zusammen)
import re
import html
from pathlib import Path

ROOT = Path(__file__).parent
BLOGS_DIR = ROOT / "blogs"
BIBLIO_DIR = ROOT / "bibliography"
TEMPLATE_FILE = ROOT / "blog_template.html"
OUT_FILE = ROOT / "blogs.html"
BIBLIO_OUT_FILE = ROOT / "bibliography.html"
POSTS_DIR = ROOT / "posts"
BIBLIO_POSTS_DIR = ROOT / "bibliography_posts"

# Template and generator are coupled through the ###...### placeholder names.
# Bump both together; the build refuses to run on a mismatch.
TEMPLATE_VERSION = 9

# Appended to styles.css and post.js as ?v=N so browsers fetch the new files
# instead of serving a cached copy. Bump when you change either.
ASSET_VERSION = 9

WORDS_PER_MINUTE = 200

# Feldfarben nach Art der edition suhrkamp, ins Kühle gezogen. Jeder Beitrag
# bekommt eine feste Farbe, abgeleitet aus seiner group_id — sie bleibt also
# gleich, auch wenn neue Beiträge dazukommen. Reihenfolge und Werte darfst du
# frei ändern; mehr oder weniger als sechs geht ebenso.
# Jeder Beitrag bekommt eine Variante desselben Prinzips: ein tiefer Grund und
# ein Metall. Das erste Paar ist zugleich der Grundton der Seite. Neue Paare darfst
# du frei ergaenzen — Schriftfarben und Kontraste rechnen sich selbst aus. Ein
# Grund muss dunkel genug fuer knochenfarbene Schrift sein.
PALETTE = [
    ('#0A1322', '#D6B46E'),  # Nacht      / Messing  — zugleich der Seitenton
    ('#0C1B14', '#C98A5E'),  # Tanne      / Kupfer
    ('#08191C', '#6FB6A6'),  # Petrol     / Gruenspan
    ('#160E1C', '#C48CA8'),  # Aubergine  / Altrosa
    ('#17120A', '#D9A441'),  # Umbra      / Bernstein
    ('#111A1F', '#A9B7C0'),  # Schiefer   / Silber
    ('#0C1226', '#9DA8DA'),  # Indigo     / Lavendel
    ('#1A0E11', '#C9614F'),  # Weinnacht  / Krapprot
]

SITE_PAIR = PALETTE[0]

BONE = '#ECE4D3'          # Schrift auf dem Farbfeld
PAPER_LIGHT = '#F4F3ED'   # Papier im hellen Modus


def _channels(hex_colour):
    h = hex_colour.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _luminance(hex_colour):
    def channel(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in _channels(hex_colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def mix(hex_colour, towards, amount):
    a, b = _channels(hex_colour), _channels(towards)
    return '#%02X%02X%02X' % tuple(
        round(x * (1 - amount) + y * amount) for x, y in zip(a, b))


def readable_on(colour, background, target=4.5):
    """Farbe ab- oder aufhellen, bis sie auf dem Grund lesbar ist.

    Betrifft Fussnotenziffern, Spaltenmarken und §-Marken: kleine Schrift, die
    denselben Kontrast braucht wie Fliesstext."""
    towards = '#000000' if _luminance(background) > 0.4 else '#FFFFFF'
    for step in range(21):
        candidate = mix(colour, towards, step * 0.05)
        if contrast(candidate, background) >= target:
            return candidate
    return colour

# Sprache in der linken Spalte der Parallelansicht.
PRIMARY_LANG = 'de'

LABELS = {
    'de': {'column': 'Deutsch', 'footnotes': 'Anmerkungen', 'published': 'Veröffentlicht', 'minutes': 'Min.'},
    'en': {'column': 'English', 'footnotes': 'Notes', 'published': 'Published', 'minutes': 'min'},
}

if not BLOGS_DIR.exists():
    print(f"blogs folder not found: {BLOGS_DIR}")
    raise SystemExit(1)

BIBLIO_DIR.mkdir(parents=True, exist_ok=True)
POSTS_DIR.mkdir(parents=True, exist_ok=True)
BIBLIO_POSTS_DIR.mkdir(parents=True, exist_ok=True)


def accent_for(group_id):
    total = sum(ord(ch) for ch in group_id)
    return PALETTE[total % len(PALETTE)]


def accent_vars(pair):
    """Alle vom Paar abgeleiteten Werte, fertig als style-Attribut.

    --ground   Farbfeld, in beiden Modi dasselbe
    --page-d   Seitengrund im dunklen Modus, aus dem Feld abgetieft
    --metal-l  Metall, auf dem hellen Papier lesbar gemacht
    --metal-d  Metall, auf dem dunklen Grund lesbar gemacht"""
    ground, metal = pair
    page_dark = mix(ground, '#000000', 0.55)
    return (
        f"--ground:{ground};"
        f"--metal:{metal};"
        f"--page-d:{page_dark};"
        f"--dim-d:{mix(BONE, page_dark, 0.45)};"
        f"--metal-l:{readable_on(metal, PAPER_LIGHT)};"
        f"--metal-d:{readable_on(metal, page_dark)}"
    )


# --------------------------------------------------------------------------
# Markdown helpers
# --------------------------------------------------------------------------

def esc(text):
    return html.escape(text, quote=True)


def inline_markdown(text):
    """Escape HTML, then re-enable **bold** and *italics* only."""
    out = esc(text)
    out = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', out)
    out = re.sub(r'\*(.+?)\*', r'<em>\1</em>', out)
    return out


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
    while i < len(lines):
        line = lines[i].strip()
        if not line or (line.startswith('<!--') and line.endswith('-->')):
            i += 1
            continue
        break

    if i >= len(lines):
        return raw

    if re.match(r'^(#{1,6})\s*.+$', lines[i].strip()):
        return '\n'.join(lines[:i] + lines[i + 1:])
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


def parse_date_from_filename(filename):
    match = re.match(r'^(\d{4}-\d{2}-\d{2})-', filename)
    if match:
        return match.group(1)
    match = re.match(r'^(\d{2})-(\d{2})-(\d{2})-', filename)
    if match:
        year, month, day = match.groups()
        return f"20{year}-{month}-{day}"
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
    german_words = ['ä', 'ö', 'ü', 'ß', ' und ', ' der ', ' die ', ' das ', ' nicht ',
                    ' ist ', ' ich ', ' sie ', ' mit ', ' für ', 'sein ', 'sich ']
    english_words = [' the ', ' and ', ' is ', ' in ', ' to ', ' of ', ' that ', ' it ',
                     ' for ', ' on ', ' with ', ' as ', ' was ', ' at ', ' be ']

    german_score = 0
    english_score = 0

    for ch in ['ä', 'ö', 'ü', 'ß']:
        if ch in sample:
            german_score += 5

    for w in german_words:
        german_score += sample.count(w)
    for w in english_words:
        english_score += sample.count(w)

    return 'de' if german_score > english_score else 'en'


def compile_markdown(markdown: str):
    """Return a list of top-level blocks so the caller can number and align them."""
    out = markdown
    out = out.replace('\\_', '_')
    out = out.replace('\r\n', '\n').replace('\r', '\n')
    out = re.sub(r'<!--\s*pair\s*:\s*[\w-]+\s*-->', '', out, flags=re.IGNORECASE)

    out = re.sub(r'### (.+?)\n', r'<h4>\1</h4>\n', out)
    out = re.sub(r'## (.+?)\n', r'<h3>\1</h3>\n', out)
    out = re.sub(r'https://([^\s<]+)(\s)', r"<a href='https://\1'>https://\1</a>\2", out)
    out = re.sub(r'```hs\n(.*?)```',
                 lambda m: f"<pre><code class='language-haskell'>{m.group(1)}</code></pre>",
                 out, flags=re.DOTALL)
    out = re.sub(r'```(.*?)```', lambda m: f"<pre><code>{m.group(1)}</code></pre>",
                 out, flags=re.DOTALL)
    out = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', out)
    out = re.sub(r'\*(.+?)\*', r'<em>\1</em>', out)

    blocks = []
    paragraph_number = 0

    for block in re.split(r'\n\s*\n', out):
        block = block.strip()
        if not block:
            continue

        if block.startswith('<h3>') or block.startswith('<h4>'):
            blocks.append({'kind': 'heading', 'html': block.replace('\n', '<br>')})
        elif block.startswith('<pre>'):
            blocks.append({'kind': 'pre', 'html': block})
        else:
            paragraph_number += 1
            blocks.append({'kind': 'para', 'html': block.replace('\n', '<br>'),
                           'number': paragraph_number})

    return blocks


def link_footnotes(text, slug, numbers):
    """Turn [^7] into a linked superscript, once the note itself exists."""
    def replace(match):
        number = int(match.group(1))
        if number not in numbers:
            return f"<sup>{number}</sup>"
        return (f"<a class='footnote-ref' id='fnref-{slug}-{number}' "
                f"href='#fn-{slug}-{number}'>{number}</a>")

    return re.sub(r'\[\^(\d+)\]', replace, text)


def render_footnotes(entry):
    if not entry['footnotes']:
        return ''

    items = ''.join(
        f"<li id='fn-{entry['slug']}-{fn['number']}'>{inline_markdown(fn['text'])}"
        f" <a class='footnote-backref' href='#fnref-{entry['slug']}-{fn['number']}'"
        f" aria-label='zurück zum Text'>&#8617;</a></li>"
        for fn in entry['footnotes']
    )

    heading = LABELS[entry['lang']]['footnotes']
    return f"<div class='footnotes'><h2>{heading}</h2><ol>{items}</ol></div>"


def reading_minutes(entry):
    words = len(re.findall(r"[\w'\u2019-]+", entry['raw']))
    return max(1, round(words / WORDS_PER_MINUTE))


def load_markdown_entries(source_dir):
    markdown_paths = [
        p.name for p in source_dir.iterdir()
        if p.suffix == ".md" and not p.name.startswith("_")
    ]
    markdown_paths.sort(key=lambda name: (parse_date_from_filename(name) or '', name), reverse=True)

    entries = []
    for filename in markdown_paths:
        path = source_dir / filename
        with path.open('r', encoding='utf-8', errors='replace') as fh:
            raw = fh.read()

        footnotes = []
        for m in re.finditer(r'^\[\^(\d+)\]:\s*(.+)$', raw, flags=re.MULTILINE):
            footnotes.append({'number': int(m.group(1)), 'text': m.group(2).strip()})
        footnotes.sort(key=lambda fn: fn['number'])

        raw_without_footnotes = re.sub(r'^\[\^\d+\]:.*(?:\n|$)', '', raw, flags=re.MULTILINE)

        title = title_from_markdown(raw_without_footnotes) or title_from_filename(filename)
        slug = create_slug(filename)
        markdown_body = strip_first_markdown_title(raw_without_footnotes)
        date = parse_date_from_filename(filename) or 'undated'
        lang = guess_language(raw_without_footnotes)
        pair_id = pair_id_from_markdown(raw_without_footnotes)
        group_id = f"{date}-{pair_id}" if pair_id else slug

        entry = {
            'name': filename,
            'date': date,
            'title': title,
            'slug': slug,
            'group_id': group_id,
            'raw': raw_without_footnotes,
            'blocks': compile_markdown(markdown_body),
            'footnotes': footnotes,
            'lang': lang,
        }
        entry['minutes'] = reading_minutes(entry)
        entries.append(entry)

    return entries


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

UNALIGNED = []


def report_unaligned():
    if not UNALIGNED:
        return
    print("\n" + "-" * 68)
    print("Absatzkopplung AUS bei folgenden Beiträgen (ungleiche Absatzzahl):")
    for group_id, counts in UNALIGNED:
        detail = ', '.join(f"{lang.upper()} {n}" for lang, n in counts)
        print(f"  {group_id}: {detail}")
    print("Die Spalten stehen nebeneinander, aber Absatz 7 links entspricht nicht")
    print("Absatz 7 rechts. Ursache sind meist Leerzeilen, die nur in einer der")
    print("beiden Markdown-Dateien stehen. Gleicht sich das an, koppelt es von selbst.")
    print("-" * 68 + "\n")


def sort_group(group_entries):
    """Primary language first, so the parallel view has a stable left column."""
    return sorted(group_entries, key=lambda e: 0 if e['lang'] == PRIMARY_LANG else 1)


def render_article(entry, rows_aligned, footnote_row):
    numbers = {fn['number'] for fn in entry['footnotes']}
    slug = entry['slug']
    pieces = []
    row = 1

    def row_style():
        return f" style='grid-row:{row}'" if rows_aligned else ""

    pieces.append(f"<p class='column-label'{row_style()}>{LABELS[entry['lang']]['column']}</p>")
    row += 1
    pieces.append(f"<h2 class='post-title'{row_style()}>{esc(entry['title'])}</h2>")
    row += 1

    for block in entry['blocks']:
        content = link_footnotes(block['html'], slug, numbers)
        if block['kind'] == 'para':
            pieces.append(
                f"<p class='para' data-p='{block['number']}' "
                f"id='p-{slug}-{block['number']}'{row_style()}>{content}</p>"
            )
        elif block['kind'] == 'heading':
            pieces.append(content.replace('>', row_style() + '>', 1))
        else:
            pieces.append(content)
        row += 1

    notes = render_footnotes(entry)
    if notes and rows_aligned:
        notes = notes.replace("<div class='footnotes'>",
                              f"<div class='footnotes' style='grid-row:{footnote_row}'>", 1)
    pieces.append(notes)

    return (f"<article id='{slug}' class='bilingual-column lang-{entry['lang']}' "
            f"lang='{entry['lang']}'>{''.join(pieces)}</article>")


def render_group(group_entries, with_header=True):
    group_entries = sort_group(group_entries)

    de_entry = next((e for e in group_entries if e['lang'] == 'de'), None)
    en_entry = next((e for e in group_entries if e['lang'] == 'en'), None)

    # Paragraph-by-paragraph alignment is only safe when both versions have the
    # same number of blocks; otherwise fall back to two independent columns.
    block_counts = {len(e['blocks']) for e in group_entries}
    rows_aligned = len(group_entries) == 2 and len(block_counts) == 1
    footnote_row = (max(block_counts) + 4) if block_counts else 4

    if len(group_entries) == 2 and not rows_aligned:
        UNALIGNED.append((
            group_entries[0]['group_id'],
            [(e['lang'], len(e['blocks'])) for e in group_entries],
        ))

    articles = ''.join(render_article(e, rows_aligned, footnote_row) for e in group_entries)

    titles = []
    if de_entry:
        titles.append(f"<h1 class='title-de' lang='de'>{esc(de_entry['title'])}</h1>")
    if en_entry:
        titles.append(f"<h1 class='title-en' lang='en'>{esc(en_entry['title'])}</h1>")
    if not titles:
        titles.append(f"<h1>{esc(group_entries[0]['title'])}</h1>")

    layout_class = 'bilingual-layout is-aligned' if rows_aligned else 'bilingual-layout'
    header = f"<div class='group-header'>{''.join(titles)}</div>" if with_header else ''

    return f"{header}<div class='{layout_class}'>{articles}</div>"


def render_band_title(group_entries, formatted_date):
    """Post titles and metadata, set inside the coloured field."""
    group_entries = sort_group(group_entries)
    de_entry = next((e for e in group_entries if e['lang'] == 'de'), None)
    en_entry = next((e for e in group_entries if e['lang'] == 'en'), None)

    titles = []
    if de_entry:
        titles.append(f"<h1 class='title-de' lang='de'>{esc(de_entry['title'])}</h1>")
    if en_entry:
        titles.append(f"<h1 class='title-en' lang='en'>{esc(en_entry['title'])}</h1>")
    if not titles:
        titles.append(f"<h1>{esc(group_entries[0]['title'])}</h1>")

    meta = render_meta_line(group_entries, formatted_date)
    return f"<div class='band-title'>{''.join(titles)}{meta}</div>"


def render_meta_line(group_entries, formatted_date):
    parts = [f"<span>{LABELS['de']['published']} {formatted_date}</span>"]
    for entry in sort_group(group_entries):
        parts.append(f"<span>{entry['minutes']} {LABELS[entry['lang']]['minutes']} "
                     f"{entry['lang'].upper()}</span>")
    return f"<p class='meta-line'>{''.join(parts)}</p>"


def nav_links(items):
    return ''.join(f"<a href='{href}'>{esc(label)}</a>" for label, href in items)


VIEW_SWITCH = (
    "<div class='view-switch' role='group' aria-label='Ansicht / View'>"
    "<button type='button' data-view='parallel' aria-pressed='true'>Parallel</button>"
    "<button type='button' data-view='de' aria-pressed='false'>Deutsch</button>"
    "<button type='button' data-view='en' aria-pressed='false'>English</button>"
    "</div>"
)


def asset(path):
    return f"{path}?v={ASSET_VERSION}"


def fill_template(template_text, target, **values):
    page = template_text
    for key, value in values.items():
        page = page.replace(f"###{key}###", value)

    leftover = sorted(set(re.findall(r'###([A-Z-]+)###', page)))
    if leftover:
        raise SystemExit(
            f"\nBuild stopped: {target} still contains unfilled placeholders: "
            + ', '.join(f'###{name}###' for name in leftover)
            + "\nblog_template.html and generate_blogs.py are from different versions."
            "\nReplace both with files from the same set and run again.\n"
        )
    return page


def render_index(posts_by_group, folder_name):
    chunks = []
    current_year = None

    for group_id, group_entries in posts_by_group.items():
        group_entries = sort_group(group_entries)
        first_entry = group_entries[0]
        group_slug = create_slug(group_id)
        year = (first_entry['date'] or 'undated')[:4]

        if year != current_year:
            if current_year is not None:
                chunks.append('</ul>')
            chunks.append(f"<h2 class='year-heading'>{esc(year)}</h2><ul class='post-index'>")
            current_year = year

        titles = ' / '.join(esc(e['title']) for e in group_entries)
        languages = ', '.join(sorted({e['lang'] for e in group_entries}))
        minutes = max(e['minutes'] for e in group_entries)

        chunks.append(
            f"<li><a href='{folder_name}/{group_slug}.html' "
            f"style='--entry:{accent_for(group_id)[1]}'>"
            f"<span class='entry-title'>{titles}</span>"
            f"<span class='entry-meta'>{format_date(first_entry['date'])} · "
            f"{languages} · {minutes} min</span></a></li>"
        )

    if current_year is not None:
        chunks.append('</ul>')

    return ''.join(chunks)


def generate_collection(entries, output_file, page_title, post_folder,
                        root_stylesheet, group_stylesheet, root_script, group_script,
                        root_back_href, group_back_href,
                        collection_label, collection_index_href,
                        index_heading=None,
                        render_single_page=False):
    posts_by_group = {}
    for entry in entries:
        posts_by_group.setdefault(entry['group_id'], []).append(entry)

    groups_html = []

    for group_id, group_entries in posts_by_group.items():
        group_entries = sort_group(group_entries)
        group_slug = create_slug(group_id)
        formatted_date = format_date(group_entries[0]['date'])
        accent = accent_for(group_id)
        group_content = render_group(group_entries, with_header=render_single_page)

        if render_single_page:
            groups_html.append(group_content)

        contents_links = ''.join(
            f"<a href='#{e['slug']}'>{e['lang'].upper()}: {esc(e['title'])}</a>"
            for e in group_entries
        )

        page_html = fill_template(
            template, str(post_folder / (group_slug + '.html')),
            **{
                'PAGE-TITLE': page_title,
                'HTML-LANG': PRIMARY_LANG,
                'BODY-CLASS': 'view-parallel single-post',
                'ACCENT-STYLE': f" style=\"{accent_vars(accent)}\"",
                'BAND-TITLE': render_band_title(group_entries, formatted_date),
                'STYLESHEET': asset(group_stylesheet),
                'SCRIPT': asset(group_script),
                'NAV-LINKS': nav_links([
                    (collection_label, collection_index_href),
                    ('Über den Autor', group_back_href.replace('index.html', 'autor.html')),
                    ('Startseite', group_back_href),
                ]),
                'VIEW-SWITCH': VIEW_SWITCH,
                'BLOG-CONTENTS': contents_links,
                'BLOGS': group_content,
            },
        )

        target_file = post_folder / f"{group_slug}.html"
        with target_file.open('w', encoding='utf-8', errors='replace') as fh:
            fh.write(page_html)

        print(f"Wrote {target_file} with {len(group_entries)} language versions.")

    if render_single_page:
        index_content = ''.join(groups_html)
        view_switch = VIEW_SWITCH
    else:
        index_content = render_index(posts_by_group, post_folder.name)
        view_switch = ''

    index_html = fill_template(
        template, str(output_file),
        **{
            'PAGE-TITLE': page_title,
            'HTML-LANG': PRIMARY_LANG,
            'BODY-CLASS': 'view-parallel',
            'ACCENT-STYLE': f" style=\"{accent_vars(SITE_PAIR)}\"",
            'BAND-TITLE': f"<div class='band-title'><h1>{esc(index_heading or page_title)}</h1></div>",
            'STYLESHEET': asset(root_stylesheet),
            'SCRIPT': asset(root_script),
            'NAV-LINKS': nav_links([
                ('Über den Autor', root_back_href.replace('index.html', 'autor.html')),
                ('Startseite', root_back_href),
            ]),
            'VIEW-SWITCH': view_switch,
            'BLOG-CONTENTS': '',
            'BLOGS': index_content,
        },
    )

    with output_file.open('w', encoding='utf-8', errors='replace') as fh:
        fh.write(index_html)

    print(f"Wrote {output_file} with {len(posts_by_group)} groups.")


blogs_data = load_markdown_entries(BLOGS_DIR)
bibliography_data = load_markdown_entries(BIBLIO_DIR)

if not TEMPLATE_FILE.exists():
    print(f"Template not found: {TEMPLATE_FILE}")
    raise SystemExit(1)

with TEMPLATE_FILE.open('r', encoding='utf-8', errors='replace') as fh:
    template = fh.read()

version_match = re.search(r'<!--\s*template-version:\s*(\d+)\s*-->', template)
found_version = int(version_match.group(1)) if version_match else 0
if found_version != TEMPLATE_VERSION:
    raise SystemExit(
        f"\nBuild stopped: blog_template.html is version {found_version}, "
        f"this script expects version {TEMPLATE_VERSION}."
        "\nReplace blog_template.html, styles.css, post.js and generate_blogs.py "
        "with files from the same set.\n"
    )


# index_heading = Überschrift auf der Verzeichnisseite,
# collection_label = Beschriftung des Rücklinks in jedem Beitrag.
generate_collection(blogs_data, OUT_FILE, 'Index', POSTS_DIR,
                    'styles.css', '../styles.css',
                    'post.js', '../post.js',
                    'index.html', '../index.html',
                    'Index', '../blogs.html',
                    index_heading='Index')

generate_collection(bibliography_data, BIBLIO_OUT_FILE, 'Bibliographie', BIBLIO_POSTS_DIR,
                    'styles.css', '../styles.css',
                    'post.js', '../post.js',
                    'index.html', '../index.html',
                    'Bibliographie', '../bibliography.html',
                    index_heading='Bibliographie',
                    render_single_page=True)

report_unaligned()