"""Altair chart builders for the screening dashboard.

Charts are pure functions of a DataFrame plus a palette, so they can be
unit-tested without a running Streamlit server.

Palette values are the validated defaults: categorical slots 1-3
(blue / orange / aqua), which clear the CVD, normal-vision, and lightness
gates in both light and dark modes.
"""

import altair as alt
import pandas as pd

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

# Score at or above which a candidate reads as a strong match.
STRONG_MATCH_THRESHOLD = 75

LIGHT = {
    "surface": "#fcfcfb",
    "text_primary": "#0b0b0b",
    "text_secondary": "#52514e",
    "muted": "#898781",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
    # Categorical slots 1-3
    "series": ["#2a78d6", "#eb6834", "#1baf7a"],
    "accent": "#2a78d6",
    "matched_fill": "#d6efd6",
    "matched_text": "#006300",
    "missing_fill": "#f0efec",
    "missing_text": "#898781",
    # Chrome only -- buttons, focus rings, links. Deliberately NOT a series
    # hue, so a control never reads as data. See BRAND_NOTE.
    "brand": "#4a3aa7",
    "brand_on": "#ffffff",
    "brand_wash": "#efedfa",
    "page": "#f9f9f7",
    "good": "#0ca30c",
    "warning": "#fab219",
    "critical": "#d03b3b",
}

DARK = {
    "surface": "#1a1a19",
    "text_primary": "#ffffff",
    "text_secondary": "#c3c2b7",
    "muted": "#898781",
    "grid": "#2c2c2a",
    "axis": "#383835",
    "series": ["#3987e5", "#d95926", "#199e70"],
    "accent": "#3987e5",
    "matched_fill": "#173d17",
    "matched_text": "#0ca30c",
    "missing_fill": "#2c2c2a",
    "missing_text": "#898781",
    "brand": "#c084fc",
    "brand_on": "#1a1a19",
    "brand_wash": "#241a33",
    "page": "#0d0d0d",
    "good": "#0ca30c",
    "warning": "#fab219",
    "critical": "#d03b3b",
}

BRAND_NOTE = """The chrome accent is violet; the chart series are blue/orange/aqua.

In light mode the two are genuinely separable (normal-vision dE 16.3 vs the
series blue, clear of the 15 floor). In dark mode they are not -- protanopia
collapses violet and blue to dE 1.9, and no fourth hue clears all three
series colours. Chrome therefore relies on placement and always-present text
labels rather than hue, which is the documented mitigation. Do not promote
this colour to a chart series."""

DIMENSIONS = [
    ("semantic_score", "Semantic"),
    ("skill_score", "Skill"),
    ("experience_score", "Experience"),
]


def get_palette(theme):
    """Return the palette for 'dark' or 'light'."""
    return DARK if theme == "dark" else LIGHT


def _style(chart, palette):
    """Apply shared chrome: recessive solid hairlines, system sans, no view border."""
    # .configure() replaces the whole config object, so it must come FIRST --
    # calling it after .configure_view() silently discards the view settings
    # and Vega's default #ddd frame comes back.
    return (
        chart.configure(background=palette["surface"], font=FONT)
        .configure_view(stroke=None, fill=palette["surface"])
        .configure_axis(
            labelFont=FONT,
            titleFont=FONT,
            labelColor=palette["muted"],
            titleColor=palette["text_secondary"],
            domainColor=palette["axis"],
            tickColor=palette["axis"],
            gridColor=palette["grid"],
            gridWidth=1,
            labelFontSize=12,
            titleFontSize=12,
            titlePadding=10,
        )
        .configure_legend(
            labelFont=FONT,
            titleFont=FONT,
            labelColor=palette["text_secondary"],
            titleColor=palette["text_secondary"],
            labelFontSize=12,
            titleFontSize=12,
            symbolType="square",
            symbolSize=110,
            orient="top",
            direction="horizontal",
            offset=12,
        )
    )


def _row_height(n, per_row=34, minimum=120):
    return max(minimum, n * per_row)


def ranking_chart(df, palette):
    """Ranked horizontal bars of final score.

    One series, so one hue for every bar. Colouring each bar by its own value
    would double-encode the bar length; the threshold rule carries the
    strong-match cutoff instead.
    """
    data = df[["filename", "final_score"]].copy()

    base = alt.Chart(data).encode(
        y=alt.Y(
            "filename:N",
            sort="-x",
            title=None,
            axis=alt.Axis(
                labelLimit=220,
                labelFontSize=13,
                labelColor=palette["text_secondary"],
                domain=False,
                ticks=False,
                labelPadding=8,
            ),
        ),
    )

    bars = base.mark_bar(
        cornerRadiusEnd=4,
        size=16,
        color=palette["accent"],
    ).encode(
        x=alt.X(
            "final_score:Q",
            title="Final ATS score (%)",
            scale=alt.Scale(domain=[0, 100]),
            axis=alt.Axis(values=[0, 25, 50, 75, 100], grid=True),
        ),
        tooltip=[
            alt.Tooltip("filename:N", title="Candidate"),
            alt.Tooltip("final_score:Q", title="Final score", format=".1f"),
        ],
    )

    # Direct label at each bar end: one value per bar, not per data point.
    labels = base.mark_text(
        align="left",
        dx=6,
        font=FONT,
        fontSize=12,
        fontWeight=600,
        color=palette["text_secondary"],
    ).encode(
        x=alt.X("final_score:Q", scale=alt.Scale(domain=[0, 100])),
        text=alt.Text("final_score:Q", format=".0f"),
    )

    threshold = (
        alt.Chart(pd.DataFrame({"v": [STRONG_MATCH_THRESHOLD]}))
        .mark_rule(color=palette["muted"], strokeWidth=1)
        .encode(x=alt.X("v:Q", scale=alt.Scale(domain=[0, 100])))
    )

    # Rule last so it stays visible across the bars it qualifies.
    chart = (bars + labels + threshold).properties(
        height=_row_height(len(data), per_row=38),
        padding={"left": 4, "right": 30, "top": 4, "bottom": 4},
    )
    return _style(chart, palette)


def breakdown_chart(df, palette):
    """Grouped bars comparing the three score dimensions per candidate.

    Three series, so the categorical palette applies and a legend is always
    shown. Per-bar numbers are deliberately omitted (that would be a number on
    every data point) -- the comparison table beside it is the table view.
    """
    long = df.melt(
        id_vars="filename",
        value_vars=[key for key, _ in DIMENSIONS],
        var_name="dimension",
        value_name="score",
    )
    long["dimension"] = long["dimension"].map(dict(DIMENSIONS))

    order = [label for _, label in DIMENSIONS]
    # Sort here rather than trusting the caller, so this chart and the
    # ranking chart always list candidates in the same order.
    candidates = list(
        df.sort_values("final_score", ascending=False)["filename"]
    )

    chart = (
        alt.Chart(long)
        .mark_bar(cornerRadiusEnd=3, size=15)
        .encode(
            y=alt.Y(
                "filename:N",
                title=None,
                sort=candidates,
                axis=alt.Axis(
                    labelLimit=220,
                    labelFontSize=13,
                    labelColor=palette["text_secondary"],
                    domain=False,
                    ticks=False,
                    labelPadding=8,
                ),
            ),
            # Surface gap between adjacent bars in a group, not a border.
            yOffset=alt.YOffset(
                "dimension:N", sort=order, scale=alt.Scale(paddingInner=0.2)
            ),
            x=alt.X(
                "score:Q",
                title="Score (%)",
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(values=[0, 25, 50, 75, 100], grid=True),
            ),
            color=alt.Color(
                "dimension:N",
                title=None,
                sort=order,
                scale=alt.Scale(domain=order, range=palette["series"]),
            ),
            tooltip=[
                alt.Tooltip("filename:N", title="Candidate"),
                alt.Tooltip("dimension:N", title="Dimension"),
                alt.Tooltip("score:Q", title="Score", format=".1f"),
            ],
        )
        .properties(height=_row_height(len(df), per_row=72, minimum=190))
    )
    return _style(chart, palette)


def skill_matrix_chart(df, palette):
    """Candidate x skill matrix showing which JD skills each resume covers.

    Binary status, encoded as fill plus a check/cross glyph -- never colour
    alone, and deliberately not a red/green pair.
    """
    rows = []
    for _, row in df.iterrows():
        for skill in row["matched_skills"]:
            rows.append(
                {"filename": row["filename"], "skill": skill, "status": "Matched"}
            )
        for skill in row["missing_skills"]:
            rows.append(
                {"filename": row["filename"], "skill": skill, "status": "Missing"}
            )

    if not rows:
        return None

    matrix = pd.DataFrame(rows)
    matrix["glyph"] = matrix["status"].map({"Matched": "✓", "Missing": "✗"})

    skills = sorted(matrix["skill"].unique())
    candidates = list(
        df.sort_values("final_score", ascending=False)["filename"]
    )

    base = alt.Chart(matrix).encode(
        x=alt.X(
            "skill:N",
            title=None,
            sort=skills,
            axis=alt.Axis(
                labelAngle=-40, labelFontSize=12, labelLimit=140,
                domain=False, ticks=False,
            ),
        ),
        y=alt.Y(
            "filename:N",
            title=None,
            sort=candidates,
            axis=alt.Axis(
                labelLimit=220,
                labelFontSize=13,
                labelColor=palette["text_secondary"],
                domain=False,
                ticks=False,
                labelPadding=8,
            ),
        ),
    )

    # Surface gap between cells rather than a border drawn around each mark.
    cells = base.mark_rect(
        stroke=palette["surface"], strokeWidth=2, cornerRadius=4
    ).encode(
        color=alt.Color(
            "status:N",
            title=None,
            scale=alt.Scale(
                domain=["Matched", "Missing"],
                range=[palette["matched_fill"], palette["missing_fill"]],
            ),
        ),
        tooltip=[
            alt.Tooltip("filename:N", title="Candidate"),
            alt.Tooltip("skill:N", title="Skill"),
            alt.Tooltip("status:N", title="Status"),
        ],
    )

    glyphs = base.mark_text(font=FONT, fontSize=13, fontWeight=600).encode(
        text=alt.Text("glyph:N"),
        color=alt.Color(
            "status:N",
            legend=None,
            scale=alt.Scale(
                domain=["Matched", "Missing"],
                range=[palette["matched_text"], palette["missing_text"]],
            ),
        ),
    )

    chart = (
        (cells + glyphs)
        .resolve_scale(color="independent")
        .properties(height=_row_height(len(candidates), per_row=42, minimum=110))
    )
    return _style(chart, palette)
