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
    out = out.replace("\\_", "_")
    out = re.sub(r"### (.+?)\n", r"<h4>\1</h4>\n", out)
    out = re.sub(r"## (.+?)\n", r"<h3>\1</h3>\n", out)
    out = re.sub(
        r"https://([^\s<]+)(\s)", r"<a href='https://\1'>https://\1</a>\2", out
    )
    out = re.sub(
        r"```hs\n(.*?)```",
        r"<pre><code class='language-haskell'>\1</code></pre>",
        out,
        flags=re.DOTALL,
    )
    out = re.sub(
        r"```(.*?)```",
        lambda m: "<pre><code>{}</code></pre>".format(m.group(1)),
        out,
        flags=re.DOTALL,
    )
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\*(.+?)\*", r"<em>\1</em>", out)
    out = out.replace("\r\n", "\n").replace("\r", "\n")
    out = out.replace("\n", "<br>")
    return out


blogs_data = []
for blog_path in blog_paths:
    path = BLOGS_DIR / blog_path
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()

    footnotes = []
    for m in re.finditer(r"^\[\^(\d+)\]:\s*(.+)$", raw, flags=re.MULTILINE):
        num = int(m.group(1))
        text = m.group(2).strip()
        footnotes.append({"number": num, "text": text})

    raw_without_footnotes = re.sub(r"^\[\^\d+\]:.*(?:\n|$)", "", raw, flags=re.MULTILINE)
   
title = title_from_filename(blog_path)
    slug = create_slug(blog_path)

    # Extract date if present
    date = None
    date_match = re.match(r'^(\d{4}-\d{2}-\d{2})-', blog_path)
    if date_match:
        date = date_match.group(1)
    else:
        date = 'undated'

    lang = guess_language(raw_without_footnotes)

    blogs_data.append({
        "name": blog_path,
        "date": date,
        "title": title,
        "slug": slug,
        "raw": raw_without_footnotes,
        "compiled": compile_markdown(raw_without_footnotes),
        "footnotes": footnotes,
        "lang": lang,
    })

if not TEMPLATE_FILE.exists():
    print(f"Template not found: {TEMPLATE_FILE}")
    raise SystemExit(1)

with TEMPLATE_FILE.open("r", encoding="utf-8", errors="replace") as fh:
    template = fh.read()


# Group posts by date for bilingual pairs
posts_by_date = {}
for entry in blogs_data:
    posts_by_date.setdefault(entry["date"], []).append(entry)

for date, entries in posts_by_date.items():
    # keep ordering as in reversed filenames (newest first)
    # slug for group page based on date and first entry
    first_entry = entries[0]
    group_slug = create_slug(f"{date}-{first_entry['title']}")

    group_nav_items = []
    group_articles = []

    for entry in entries:
        entry_anchor = f"#{entry['slug']}"
        group_nav_items.append(f"<a href='{entry_anchor}'>- {entry['lang'].upper()}: {entry['title']}</a>")

        # footnote script block per entry
        script_block = ""
        if entry.get("footnotes"):
            calls = []
            for fn in entry["footnotes"]:
                text_js = json.dumps(fn["text"])
                calls.append(f'  window.addFootnote("{entry["slug"]}", {fn["number"]}, {text_js});')
            script_block = (
                "<script>document.addEventListener('DOMContentLoaded', function() {\n"
                + "\n".join(calls)
                + "\n});</script>"
            )

        article_html = (
            f"<article id=\"{entry['slug']}\" class=\"bilingual-column lang-{entry['lang']}\">\n"
            f"<h2>{'Deutsch' if entry['lang'] == 'de' else 'English'}</h2>\n"
            f"<h1 class=\"post-title\">{entry['title']}</h1>\n"
            f"<p class=\"post-date\">{entry['date']}</p>\n"
            f"{entry['compiled']}\n"
            f"{script_block}\n"
            f"</article>"
        )

        group_articles.append(article_html)

    group_content = (
        f"<div class='group-header'><h1>{first_entry['title']} ({date})</h1>"
        f"<p class='group-subtitle'>Bilingual overview with side-by-side language panes.</p></div>\n"
        f"<nav aria-label='Post languages'>\n{''.join([f'<span class="lang-chip">{i.split(':')[0]}</span>' for i in [g.split('</a>')[0] for g in group_nav_items]])}</nav>\n"
        f"<div class='bilingual-layout'>\n{''.join(group_articles)}\n</div>"
    )

    group_idx_html = "<br>".join(group_nav_items)
    page_html = template.replace("###BLOG-CONTENTS###", group_idx_html)
    page_html = page_html.replace("###BLOGS###", group_content)

    # Add bilingual mode body class, using simple replace to preserve existing body tag
    page_html = page_html.replace('<body>', '<body class="bilingual-mode">')

    target_file = POSTS_DIR / f"{group_slug}.html"
    with target_file.open("w", encoding="utf-8", errors="replace") as fh:
        fh.write(page_html)

    print(f"Wrote {target_file} with {len(entries)} language versions.")

# Build index page with group listing
index_items = []
for date, entries in posts_by_date.items():
    first_entry = entries[0]
    group_slug = create_slug(f"{date}-{first_entry['title']}")
    lang_labels = ", ".join(sorted({entry['lang'] for entry in entries}))
    index_items.append(
        f"<li><a href='posts/{group_slug}.html'>{date} – {first_entry['title']} ({lang_labels})</a></li>"
    )

index_content = (
    "<header><h1>Blog Index</h1><p>Click a topic to open per-post bilingual page.</p></header>"
    f"<main><ul class='post-index'>{''.join(index_items)}</ul></main>"
)

index_html = template.replace("###BLOG-CONTENTS###", "")
index_html = index_html.replace("###BLOGS###", index_content)

with OUT_FILE.open("w", encoding="utf-8", errors="replace") as fh:
    fh.write(index_html)

print(f"Wrote {OUT_FILE} with {len(posts_by_date)} groups.")
