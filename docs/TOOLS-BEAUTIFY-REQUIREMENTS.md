# Tools · Format / Beautify a reading — business requirements

## Purpose

From the **Tools** menu, an editor uploads a **YouTube captions `.txt` file**, then chooses one of two prepare actions:

| Action | What it does |
|--------|----------------|
| **Format the reading** | Keep **every original word**. Only punctuation + paragraph breaks. Downloads HTML. |
| **Beautify** | Shape a pleasant Kindle reading (or newsletter blurb) in Lakshmi-style presentation — not a word-for-word caption dump. Downloads **one** HTML file in the chosen output language. |

Site placement under `content/readings/` stays a separate step (`article_reading.py --fragment` or manual).

## Reference presentation

| Piece | Role | Style |
|-------|------|--------|
| Formatted full reading | Faithful transcript for Kindle / site | **Format** |
| Beautified full reading | Conversation-style spoken reading | **Beautify** (blurb off) |
| Newsletter blurb | Short third-person summary + “read more” on site | **Beautify** + Blurb content |

Reference process notes: `docs/Prompt.txt`.

## Scope

| In scope | Out of scope |
|----------|----------------|
| Captions `.txt` → Format or Beautify HTML download | Inventing teachings not in the source |
| English, Telugu, or Kannada | Translation (except optional later EN+TE blurb pair) |
| Download HTML from Format and Beautify | Save popup / auto-write into `content/readings/` |
| Beautify output language checkboxes (original / English / Hindi) | Format translating (Format stays same-language only) |
| Local Tools only | Prepare on published GitHub Pages |

## Actors

- **Editor / sevak** — uploads captions, chooses Format or Beautify (and blurb / word limit / speaker), downloads HTML when ready.

## End-to-end flow

1. Choose a captions `.txt` file.
2. Either:
   - **Format the reading** → faithful punctuation HTML → **download**; or
   - Set output language / Blurb / Word limit / Speaker as needed → **Beautify** → shaped HTML → **download**.
3. Open the downloaded file locally; place into the site later if needed.

## Tools UI — prepare

1. **Captions file** — `.txt` (YouTube captions). Required.
2. **Speaker only** — optional text field (applies to **Format** and **Beautify**).  
   - Empty → use the whole caption file.  
   - Filled (e.g. `Dr. Lakshmi Newton`, `లక్ష్మి మేడం`, `Newton`) → keep only that speaker’s spoken parts; drop hosts, others, and stage chatter that are clearly not them.  
   - Needed when the YouTube file is a multi-speaker event; skip when the file is already one speaker.
3. **Output language** — checkboxes (applies to **Beautify** only; check one or more).  
   - **Original transcript language** (checked by default).  
   - **English** → `…-en.html`.  
   - **Hindi** → `…-hi.html`.  
   - Downloads one HTML file per checked language.  
   - Ignored for **Format the reading** (always original language).
4. **Blurb content** — checkbox (applies to **Beautify** only).  
   - Unchecked → beautified full reading.  
   - Checked → newsletter blurb.  
   - Ignored for **Format the reading**.
5. **Word limit** — number field (applies to **Beautify** only).  
   - Prefill **2500** (full beautify) / **450** (blurb).  
   - Empty → no hard cap (blurb still stays concise, prefer under ~800).  
   - Ignored for **Format the reading** (always full spoken content of the selected speaker / file).
6. **Format the reading** — faithful method; downloads HTML.
7. **Beautify** — shaped full reading or blurb; downloads one HTML file per checked language.

## Format the reading (must)

From `docs/Prompt.txt` — used when the editor wants the **full speech with every word kept**:

1. Do **not** change any original text.
2. Only add full stops, commas, quotation marks, and other punctuation so it feels like natural speech.
3. Follow context, intention, and spiritual wisdom. Never alter meaning or words.
4. Proper paragraph breaks for pleasant Kindle reading (parchment HTML).
5. Preserve every original word exactly. Only punctuation and paragraph structure are added.
6. Blockquotes / sparse emphasis only where they do not change or drop words.
7. No section headings. No word-limit truncation.
8. Result downloads as HTML.

## Beautify (must work differently from Format)

Beautify is **not** the faithful punctuation pass.

### Beautify — full reading (Blurb unchecked)

1. Conversation-style spoken reading (Lakshmi birthday **full reading** quality bar).
2. Speaker’s voice; short breath-like paragraphs; stories as beats; pull-out dialogue with connective lines.
3. May lightly smooth awkward caption grammar for pleasant Kindle reading — **same ideas and order**, same language — but it is allowed to shape sentences for reading comfort (unlike Format).
4. Sparse bold (names / key terms) and italic where helpful.
5. Word limit when set ≈ ceiling; empty = full arc without a hard cap.
6. No section headings.
7. Downloads one HTML file per checked output language.

### Beautify — blurb (Blurb checked)

1. Third-person newsletter blurb; excite the reader about what happened; stay true to content (`Prompt.txt` blurb variation).
2. Default word limit **450**; process allows under ~**800** if raised.
3. Few pull-out quotes.
4. Downloads one HTML file per checked output language.

## Optional later

- More output languages beyond English / Hindi.

## Constraints

1. Local reader only; Pages does not run prepare.
2. Gemini API key required for Format and Beautify.

## Success criteria

- [x] `.txt` captions input.
- [x] **Format the reading** = every word kept; punctuation + paragraphs; download HTML.
- [x] **Beautify** = different prompt/behaviour (shaped full reading or blurb); download one HTML per checked language (original default / English / Hindi).
- [x] Blurb + word limit apply to Beautify only.
- [x] Optional Speaker only field filters multi-speaker captions when set.
- [x] No save-to-readings popup; download only.
- [ ] Language and meaning preserved; no invented teaching.
