import re, sys, os
import pymupdf
path = sys.argv[1] if len(sys.argv) > 1 else "DataChallenge_Team AIC023_Report.pdf"
d = pymupdf.open(path)
print("pages", d.page_count)
heads = {}
for i, p in enumerate(d, 1):
    if i == 1:
        continue
    t = p.get_text()
    for key, pat in [("Summary", r"\nSummary\n"), ("Intro", r"\n1\. Introduction\n"), ("Method", r"\n2\. Methodology\n"),
                     ("Findings", r"\n3\. Findings\n"), ("Discussion", r"\n4\. Discussion\n"), ("Recs", r"\n5\. Recommendations\n"),
                     ("References", r"\nReferences\n"), ("AppA", r"Appendix A\. AI usage")]:
        if re.search(pat, "\n" + t) and key not in heads:
            heads[key] = i
print(heads)
ref = heads.get("References")
body_pages = ref - 2 if ref else None
print("body pages (Summary start to References start, exclusive):", ref - heads["Summary"])
words = 0
for i in range(heads["Summary"], ref):
    t = d[i - 1].get_text()
    t = "\n".join(l for l in t.splitlines() if not l.startswith("Data Challenge 2026") and not re.match(r"^(Team AIC023|Page \d+|Back to contents)", l.strip()))
    words += len(t.split())
print("body words (incl. captions/tables):", words)
links = sum(len(p.get_links()) for p in d)
print("links:", links, " outline entries:", len(d.get_toc()))
for lvl, title, pg in d.get_toc()[:30]:
    print("  ", lvl, title, pg)
if "--png" in sys.argv:
    out = os.path.join("pages")
    os.makedirs(out, exist_ok=True)
    for i, p in enumerate(d, 1):
        p.get_pixmap(dpi=70).save(os.path.join(out, f"p{i:02d}.png"))
