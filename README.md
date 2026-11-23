# pssm-self-knowledge

Local welcome page for Pyramid Spiritual Societies Movement self-knowledge work.

Pages use the parchment stylesheet from the [9-Day Anapanasati programme](https://anemdhana.github.io/awakening-the-wisdom-within/Session-Schedules/9-Day-Anapanasati-Meditation-Spiritual-Seed/index.html). The reading text lives once under `content/`. `pages.py` wraps it in one layout. The Python server renders that locally, and GitHub Actions publishes the same pages.

The first reading series is the 9-day Anapanasati programme from Spiritual Seed (Priyanka), taken from [`awakening-the-wisdom-within-1`](../awakening-the-wisdom-within-1). Rebuild the reading pages with `python scripts/build_anapanasati_series.py`.

Companion to [`pssm-swadhyaya-notes`](../pssm-swadhyaya-notes).

## Start

Python 3.10+ on PATH is enough. No extra packages.

```powershell
cd c:\Users\dhana\GitHub\pssm-self-knowledge
.\start.cmd
```

Opens **http://127.0.0.1:8766/**. Keep the window open. Page edits reload the browser. Ctrl+C stops the server.

```powershell
python serve.py
```

## GitHub Pages

Pushing `main` runs `.github/workflows/pages.yml`, which builds the same pages with `python scripts/build_site.py`. In the repository settings, set Pages to **GitHub Actions** once. The site is then at `https://anemdhana.github.io/pssm-self-knowledge/`.

## Layout

```text
pssm-self-knowledge/
  site.json          menu, authors, and shared page chrome
  pages.py           one layout for the server and for Pages
  content/           reading text only
  static/            css, shell.js, portraits
  serve.py
  scripts/build_site.py
```
