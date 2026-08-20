"""Chrome styling for the dashboard: brand accent, texture, button states.

Kept out of dashboard.py so the CSS can be built and asserted on in tests.

Scope discipline: everything here styles *chrome* -- surfaces, buttons,
cards, the header band. None of it touches chart marks. Texture in
particular is deliberately confined to chrome; dense angled fills laid over
data read as noise and are a vestibular risk, so the charts stay flat.
"""


def rgba(hex_colour, alpha):
    """'#4a3aa7', 0.05 -> 'rgba(74, 58, 167, 0.05)'."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def fit_band_colour(score, palette, threshold):
    """Status colour for a final score. Always paired with a text label."""
    if score >= threshold:
        return palette["good"]
    if score >= 50:
        return palette["warning"]
    return palette["critical"]


def page_css(palette):
    """The full <style> block, built against the active palette."""
    brand = palette["brand"]
    surface = palette["surface"]

    # One hairline diagonal every 8px, at very low alpha. Present on the
    # header band only -- never behind text-heavy or data regions.
    texture = (
        f"repeating-linear-gradient(45deg, transparent 0 7px, "
        f"{rgba(brand, 0.055)} 7px 8px)"
    )

    return f"""
    <style>
      .block-container {{ padding-top: 1.7rem; max-width: 1500px; }}

      /* ---------------------------------------------------- header band -- */
      .hero {{
        position: relative;
        overflow: hidden;
        border: 1px solid {palette['grid']};
        border-radius: 14px;
        padding: 1.3rem 1.5rem;
        margin-bottom: 1.15rem;
        background:
          {texture},
          linear-gradient(135deg, {palette['brand_wash']} 0%, {surface} 60%);
      }}
      .hero::after {{
        content: "";
        position: absolute;
        top: -70px; right: -50px;
        width: 240px; height: 240px;
        border-radius: 50%;
        background: radial-gradient(circle, {rgba(brand, 0.16)} 0%,
                                    transparent 68%);
        pointer-events: none;
      }}
      .hero-eyebrow {{
        font-size: .7rem; font-weight: 700; letter-spacing: .1em;
        text-transform: uppercase; color: {brand}; margin-bottom: .35rem;
      }}
      .hero h1 {{
        font-size: 1.6rem; font-weight: 660; letter-spacing: -.022em;
        margin: 0 0 .25rem; color: {palette['text_primary']}; padding: 0;
      }}
      .hero p {{
        font-size: .92rem; color: {palette['text_secondary']};
        margin: 0; line-height: 1.55;
      }}

      .page-title {{
        font-size: 1.15rem; font-weight: 640; letter-spacing: -.015em;
        margin: 0 0 .15rem; color: {palette['text_primary']};
      }}
      .page-sub {{
        font-size: .93rem; color: {palette['text_secondary']}; margin: 0;
      }}

      /* -------------------------------------------------------- buttons -- */
      .stButton > button, .stDownloadButton > button {{
        font-weight: 550;
        transition: transform .12s ease, box-shadow .12s ease,
                    border-color .12s ease, background-color .12s ease;
      }}
      .stButton > button:hover:not(:disabled),
      .stDownloadButton > button:hover:not(:disabled) {{
        transform: translateY(-1px);
        box-shadow: 0 5px 16px {rgba(brand, 0.24)};
        border-color: {brand};
      }}
      .stButton > button:active:not(:disabled),
      .stDownloadButton > button:active:not(:disabled) {{
        transform: translateY(0);
        box-shadow: 0 2px 6px {rgba(brand, 0.18)};
      }}
      /* Disabled must not appear interactive. */
      .stButton > button:disabled, .stDownloadButton > button:disabled {{
        opacity: .5;
        transform: none !important;
        box-shadow: none !important;
        cursor: not-allowed;
      }}
      /* Keyboard focus stays visible; mouse focus does not draw a ring. */
      .stButton > button:focus-visible,
      .stDownloadButton > button:focus-visible {{
        outline: 2px solid {brand};
        outline-offset: 2px;
      }}

      /* ---------------------------------------------------- stat tiles --- */
      [data-testid="stMetric"] {{
        background: linear-gradient(160deg, {palette['brand_wash']} 0%,
                                    {surface} 72%);
        border-radius: 12px;
        transition: box-shadow .14s ease;
      }}
      [data-testid="stMetric"]:hover {{
        box-shadow: 0 3px 12px {rgba(brand, 0.12)};
      }}

      /* -------------------------------------------------------- chips ---- */
      .chip-row {{ display: flex; flex-wrap: wrap; gap: 6px; margin: .15rem 0 .6rem; }}
      .chip {{
        font-size: .78rem; font-weight: 500; padding: 3px 11px;
        border-radius: 999px; line-height: 1.6; white-space: nowrap;
        border: 1px solid transparent;
      }}
      .chip-ok {{
        background: {palette['matched_fill']}; color: {palette['matched_text']};
        border-color: {rgba(palette['matched_text'], 0.22)};
      }}
      .chip-no {{
        background: {palette['missing_fill']}; color: {palette['missing_text']};
        border-color: {rgba(palette['missing_text'], 0.25)};
      }}
      .chip-none {{
        font-size: .82rem; color: {palette['muted']}; font-style: italic;
      }}

      .field-label {{
        font-size: .74rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: .06em; color: {palette['muted']}; margin: .1rem 0 .3rem;
      }}

      /* ------------------------------------------------ candidate cards -- */
      .rank-badge {{
        display: inline-flex; align-items: center; justify-content: center;
        min-width: 26px; height: 26px; padding: 0 7px; border-radius: 8px;
        background: {brand}; color: {palette['brand_on']};
        font-size: .82rem; font-weight: 650; margin-right: .55rem;
      }}
      .cand-name {{
        font-size: 1.02rem; font-weight: 620; color: {palette['text_primary']};
      }}

      /* ---------------------------------------------------- empty state -- */
      .empty-state {{
        padding: 2.6rem 1rem; text-align: center;
        border-radius: 12px;
        background: {texture};
      }}
      .empty-state h3 {{
        font-size: 1.05rem; font-weight: 600; margin: 0 0 .4rem;
        color: {palette['text_primary']};
      }}
      .empty-state p {{
        font-size: .9rem; color: {palette['text_secondary']}; margin: 0 auto;
        max-width: 460px; line-height: 1.6;
      }}

      @media (prefers-reduced-motion: reduce) {{
        .stButton > button, .stDownloadButton > button,
        [data-testid="stMetric"] {{ transition: none; }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
          transform: none;
        }}
      }}
    </style>
    """


def card_accent_css(accents):
    """A coloured left edge per candidate card.

    accents: iterable of (container_key, colour). Streamlit renders a
    container with key="x" inside an element carrying the class "st-key-x",
    which is what these rules hang off.
    """
    rules = "".join(
        f'.st-key-{key} {{ border-left: 3px solid {colour} !important; }}'
        for key, colour in accents
    )
    return f"<style>{rules}</style>"


def hero_html(title, subtitle, eyebrow="Applicant tracking"):
    import html as _html

    return (
        '<div class="hero">'
        f'<div class="hero-eyebrow">{_html.escape(eyebrow)}</div>'
        f"<h1>{_html.escape(title)}</h1>"
        f"<p>{subtitle}</p>"
        "</div>"
    )
