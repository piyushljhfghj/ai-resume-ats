# Intelligent Resume Screening System

An ATS-style engine that ranks resumes against a job description using
semantic similarity, weighted skill matching, and experience extraction.

## Running

Install dependencies:

```
pip install -r requirements.txt
```

Dashboard (Streamlit):

```
streamlit run dashboard.py
```

Inputs live in the sidebar; results fill the main pane across three tabs:

- **Overview** - KPI row, ranked score chart, and a top-match card.
- **Compare** - per-dimension breakdown, the full score table, and a
  candidate x skill coverage matrix.
- **Candidates** - a card per candidate with matched/missing skill chips
  and a PDF report.

Results are held in session state, so downloading a report does not clear
the page. Charts follow the active Streamlit theme in both light and dark.

API (FastAPI):

```
uvicorn api:app --reload
```

### `POST /rank`

```json
{
  "job_description": "Required: Python and machine learning.",
  "resumes": ["resume text 1", "resume text 2"],
  "resume_names": ["alice.txt", "bob.txt"]
}
```

Returns `total_candidates` and a `ranking` array sorted best-first.
`resumes` and `resume_names` must be the same length.

## Scoring

```
Final Score = 0.4 * Semantic Similarity
            + 0.4 * Weighted Skill Match
            + 0.2 * Experience Match
```

Weights live in `app/config.py`.

- **Semantic** — cosine similarity between JD and resume embeddings
  (`all-mpnet-base-v2`).
- **Skill** — required skills count double the weight of preferred ones.
  A skill named in both halves of the JD counts once, as required.
- **Experience** — explicit durations ("5+ years") and date ranges
  ("2020 – Present"). Overlapping ranges are merged, not summed.

A dimension the JD says nothing about scores neutral (100) rather than 0,
so it does not silently cap every candidate's total.

## Baselines

Two comparison rankers are runnable as scripts:

```
python -m app.main               # TF-IDF
python -m app.embedding_ranker   # embeddings
```

## Tests

```
pip install -r requirements-dev.txt
pytest
```

The suite stubs the embedding model, so it runs in under a second and
never downloads weights.

## Colour & chrome

Two colour systems, deliberately kept apart:

- **Chart series** - blue / orange / aqua (`app/charts.py`). Identity of data.
- **Chrome accent** - violet (`brand` in the same palette). Buttons, focus
  rings, links, rank badges. Never used for a mark.

`charts.BRAND_NOTE` records the caveat: in light mode the violet is genuinely
separable from the series blue (normal-vision dE 16.3, clear of the 15 floor),
but in dark mode protanopia collapses violet and blue to dE 1.9, and no fourth
hue clears all three series colours. Chrome therefore leans on placement and
always-present text labels, not hue. Do not promote the brand colour to a
chart series.

Status colours (`good` / `warning` / `critical`) drive the fit badge and the
coloured left edge on each candidate card. They always ship with an icon and a
text label, never colour alone, and are distinct from every series hue.

`app/ui_theme.py` holds the chrome CSS: button hover/active/disabled/focus
states, stat-tile tinting, skill chips, and the header band. Texture -- a 45
degree hairline every 8px at ~5% alpha -- appears on the header band and empty
state **only**. It is never laid over chart marks, where dense angled fills
read as noise and are a vestibular risk. A `prefers-reduced-motion` block
disables the button transitions.

Note that Vega-Lite cannot do true hatch/pattern fills on marks (fills must be
colour strings), so chart-level texture is not an option even if wanted; the
accessibility channel there is the check/cross glyph in the skill matrix and
the direct value labels on the ranking chart.

## Charts

`app/charts.py` builds every chart as a pure function of a DataFrame plus a
palette, so they are unit-testable without a running server. Altair ships
with Streamlit, so there is no separate charting dependency.

The palette is the validated categorical default (blue / orange / aqua),
which clears the colour-vision, normal-vision, and lightness gates in both
modes. Two rules worth keeping if you edit these:

- The ranking chart uses **one hue for every bar**. Colouring bars by their
  own value would double-encode the bar length.
- The skill matrix carries status as a check/cross glyph as well as fill,
  so it never depends on colour alone. That needs
  `resolve_scale(color="independent")` -- otherwise the layers share one
  colour scale and the glyphs render in the cell fill colour, invisible.

`_style()` calls `.configure()` **before** `.configure_view()`. Altair's
`.configure()` replaces the whole config object, so the reverse order
silently drops the view settings and Vega's default frame returns.

## Architecture notes

- `app/model_loader.get_model()` is the only place the model is
  instantiated. Constructing `SentenceTransformer` elsewhere loads a
  second ~420MB copy.
- `rank_texts(jd, [(name, text), ...])` is the core entry point and takes
  plain strings. `rank_resumes(jd, uploaded_files)` wraps it for file
  uploads. A file that cannot be read is skipped and logged, not fatal.

## Limitations

- Skill matching is limited to a fixed vocabulary in `app/skill_extractor.py`.
- Required/preferred detection splits the JD on the first "preferred".
- No labeled dataset; manual skill weights.
- No bias mitigation or fairness testing.

### Fairness Consideration

The system may introduce bias through manual skill weighting, keyword-based
matching, and a lack of demographic fairness testing. Future versions should
include bias audits and fairness metrics.
