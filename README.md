# pssm-self-knowledge

Local welcome page for Pyramid Spiritual Societies Movement self-knowledge work.

Pages use the parchment stylesheet from the [9-Day Anapanasati programme](https://anemdhana.github.io/awakening-the-wisdom-within/Session-Schedules/9-Day-Anapanasati-Meditation-Spiritual-Seed/index.html) (`css/site.css`). A small Python server opens the site locally, the same way [`qlu-newsletter-tools`](../qlu-newsletter-tools) does.

The first reading series is the 9-day Anapanasati programme from Spiritual Seed (Priyanka), taken from [`awakening-the-wisdom-within-1`](../awakening-the-wisdom-within-1). Rebuild the reading pages with `python scripts/build_anapanasati_series.py`.

Companion to [`pssm-swadhyaya-notes`](../pssm-swadhyaya-notes).

## Start

Python 3.10+ on PATH is enough. No extra packages.

```powershell
cd c:\Users\dhana\GitHub\pssm-self-knowledge
.\start.cmd
```

Opens **http://127.0.0.1:8766/**. Keep the window open. Ctrl+C stops the server.

```powershell
python serve.py
```

## Layout

```text
pssm-self-knowledge/
  README.md
  start.cmd
  serve.py
  scripts/
    check_python_env.py
  docs/
    index.html
    shell.js
    css/site.css
    css/shell.css
    readings/9-day-anapanasati/
    readings/brahmarshi-patriji/
    assets/
      pssm-logo.png
```
