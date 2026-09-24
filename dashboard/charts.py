"""
Shared chart styling for the dashboard -- one place to keep every page's
Plotly figures visually consistent (same palette used in the notebooks).
"""

import plotly.express as px
import plotly.graph_objects as go

# Fixed categorical order (never cycled), and a single-hue sequential ramp
# for magnitude (e.g. cohort heatmaps).
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#184f95"]

TEMPLATE = "plotly_white"


def line_chart(df, x, y, title, y_title=None):
    fig = px.line(df, x=x, y=y, markers=True, color_discrete_sequence=[CATEGORICAL[0]], title=title)
    fig.update_layout(template=TEMPLATE, xaxis_title=None, yaxis_title=y_title or y)
    return fig


def bar_chart(df, x, y, title, y_title=None, color=None):
    fig = px.bar(df, x=x, y=y, color=color or x, color_discrete_sequence=CATEGORICAL, title=title)
    fig.update_layout(template=TEMPLATE, showlegend=False, xaxis_title=None, yaxis_title=y_title or y)
    return fig


def funnel_chart(df, stage_col, value_col, title):
    fig = go.Figure(go.Funnel(
        y=df[stage_col], x=df[value_col],
        marker={"color": CATEGORICAL[0]},
        textinfo="value+percent initial",
    ))
    fig.update_layout(template=TEMPLATE, title=title)
    return fig


def heatmap(pivot_df, title, x_title, y_title, color_title="Value"):
    fig = px.imshow(
        pivot_df, color_continuous_scale=SEQUENTIAL_BLUE,
        labels=dict(x=x_title, y=y_title, color=color_title),
        text_auto=True, aspect="auto", title=title,
    )
    fig.update_layout(template=TEMPLATE)
    return fig
