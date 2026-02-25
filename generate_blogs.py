import os
import re
import json
from pathlib import Path

ROOT = Path(__file__).parent
BLOGS_DIR = ROOT / "blogs"
TEMPLATE_FILE = ROOT / "blog_template.html"
OUT_FILE = ROOT / "blogs.html"

# Get all markdown files in the blogs folder, ignoring those starting with underscore.
if not BLOGS_DIR.exists():
    print(f"blogs folder not found: {BLOGS_DIR}")
    raise SystemExit(1)

blog_paths = [p.name for p in BLOGS_DIR.iterdir() if p.suffix == ".md" and not p.name.startswith("_")]

# Start with the latest blog
blog_paths = list(reversed(blog_paths))

# Read each blog, extract footnote definitions, and keep both content and extracted footnotes
blogs_data = []
for blog_path in blog_paths:
    path = BLOGS_DIR / blog_path
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()

    # Extract footnote definitions of the form [^1]: text
    footnotes = []
    for m in re.finditer(r"^\[\^(\d+)\]:\s*(.+)$", raw, flags=re.MULTILINE):
        num = int(m.group(1))
        text = m.group(2).strip()
        footnotes.append({"number": num, "text": text})

    # Remove footnote definition lines from the content
    raw = re.sub(r"^\[\^\d+\]:.*(?:\n|$)", "", raw, flags=re.MULTILINE)

    blogs_data.append({"name": blog_path, "raw": raw, "footnotes": footnotes})

if not TEMPLATE_FILE.exists():
    print(f"Template not found: {TEMPLATE_FILE}")
    raise SystemExit(1)

with TEMPLATE_FILE.open("r", encoding="utf-8", errors="replace") as fh:
    template = fh.read()

# Replace markdown with HTML tags
def compile_markdown(markdown: str):
    out = markdown
    # Unescape escaped underscores in URLs (e.g. \_ -> _)
    out = out.replace("\\_", "_")
    out = re.sub(r"### (.+?)\n", r"<h4>\1</h4>\n", out)
    out = re.sub(r"## (.+?)\n", r"<h3>\1</h3>\n", out)
    out = re.sub(r"https://([^\s<]+)(\s)", r"<a href='https://\1'>https://\1</a>\2", out)
    # handle fenced code blocks before turning newlines into <br>
    out = re.sub(r"```hs\n(.*?)```", r"<pre><code class='language-haskell'>\1</code></pre>", out, flags=re.DOTALL)
    out = re.sub(r"```(.*?)```", lambda m: "<pre><code>{}</code></pre>".format(m.group(1)), out, flags=re.DOTALL)
    # Bold and italic (Markdown) -> HTML (only * syntax to avoid interfering with URLs containing underscores)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\*(.+?)\*", r"<em>\1</em>", out)
    out = out.replace("\r\n", "\n").replace("\r", "\n")
    out = out.replace("\n", "<br>")
    return out

# Inline testing
assert compile_markdown("```hello```") == "<pre><code>hello</code></pre>"
# function replaces trailing newline with <br>, adjust expected strings accordingly
assert compile_markdown("## Title\n") == "<h3>Title</h3><br>"
assert compile_markdown("### Subtitle\n") == "<h4>Subtitle</h4><br>"
# Italics and bold
assert compile_markdown("This is *italics*\n") == "This is <em>italics</em><br>"
assert compile_markdown("This is **bold**\n") == "This is <strong>bold</strong><br>"
# Links with escaped underscores
assert compile_markdown("See https://de.wikipedia.org/wiki/Die\\_schlesischen\\_Weber\n") == "See <a href='https://de.wikipedia.org/wiki/Die_schlesischen_Weber'>https://de.wikipedia.org/wiki/Die_schlesischen_Weber</a><br>"

# Compile markdown content for each blog
for entry in blogs_data:
    entry["compiled"] = compile_markdown(entry["raw"])

# Create slug from filename for use as article ID
def create_slug(filename):
    # Remove .md extension and convert to URL-friendly slug
    slug = filename.replace('.md', '')
    slug = re.sub(r'[^a-z0-9]+', '-', slug.lower())
    slug = slug.strip('-')
    # Ensure slug doesn't start with a number
    if slug and slug[0].isdigit():
        slug = 'post-' + slug
    return slug

# Create the contents page at the top of the blog which links to each blog on the page
blog_contents = [f"<a href='#{create_slug(name)}'>- {name}</a>" for name in blog_paths]

# Wrap each blog in <article> tags with proper ID and embed inline scripts to register footnotes
blogs_with_articles = []
for entry in blogs_data:
    name = entry["name"]
    blog = entry.get("compiled", "")
    slug = create_slug(name)

    # If there are extracted footnotes, emit a small inline script that will call window.addFootnote
    script_block = ""
    if entry.get("footnotes"):
        calls = []
        for fn in entry["footnotes"]:
            # Use json.dumps to safely encode the footnote text as a JS string literal
            text_js = json.dumps(fn["text"])
            calls.append(f'  window.addFootnote("{slug}", {fn["number"]}, {text_js});')

        script_block = "<script>document.addEventListener('DOMContentLoaded', function() {\n" + "\n".join(calls) + "\n});</script>"

    article_html = f'<article id="{slug}">\n{blog}\n{script_block}\n</article>'
    blogs_with_articles.append(article_html)

blog_html = template.replace("###BLOGS###", "\n<hr>\n".join(blogs_with_articles))
blog_html = blog_html.replace("###BLOG-CONTENTS###", "<br>".join(blog_contents))

with OUT_FILE.open("w", encoding="utf-8", errors="replace") as fh:
    fh.write(blog_html)

print(f"Wrote {OUT_FILE} with {len(blogs_with_articles)} posts.")