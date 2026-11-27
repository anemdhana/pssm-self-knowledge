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

## Tools

The top menu **Tools** page takes a YouTube captions **`.txt`** file. **Format the reading** keeps every original word (punctuation + paragraphs) and downloads one HTML file. **Beautify** shapes a pleasant full reading or newsletter blurb (word limit defaults 2500 / 450) and downloads one HTML file per checked output language: original transcript language (checked by default), English (`…-en.html`), and/or Hindi (`…-hi.html`). Optional **Speaker only** keeps one speaker from multi-speaker captions. Use `scripts/article_reading.py --fragment` later if you want a site fragment under `content/readings/`.

Put a free key from [Google AI Studio](https://aistudio.google.com/apikey) in `.env` as `GEMINI_API_KEY`. The CLI still works:

```powershell
python scripts/beautify_reading.py captions.txt --mode format
python scripts/beautify_reading.py captions.txt --mode beautify
python scripts/beautify_reading.py captions.txt --mode beautify --lang en
python scripts/beautify_reading.py captions.txt --mode beautify --lang hi
python scripts/beautify_reading.py captions.txt --mode beautify --blurb --words 450
```

This step runs on the local server. The published GitHub Pages site does not call the model.

`scripts/article_reading.py` turns an HTML file into an article reading: the title, the date, then the text. The date is taken from a date line, a `<time>` tag, or the title. When the HTML has no date, the date is today. A leading “Newsletter blurb:” or “న్యూస్‌లెటర్ బ్లర్బ్:” is left off the title.

```powershell
python scripts/article_reading.py talk.html
python scripts/article_reading.py talk.html --date 2026-11-24 --author "Dr. Lakshmi Newton"
python scripts/article_reading.py talk.html --fragment --chrome lakshmi -o content/readings/talk.html
```

The first command writes `talk-reading.html` beside the source. The last one writes a site fragment, and the date appears under the speaker’s name.

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
  scripts/beautify_reading.py
  scripts/article_reading.py
```
