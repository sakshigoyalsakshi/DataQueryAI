import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def build_figure(
    df: pd.DataFrame,
    viz_type: str,
    viz_config: dict,
) -> "go.Figure | None":
    """
    Build a Plotly figure from LLM-recommended viz_type and viz_config.
    Returns None for 'table' and 'text' types (handled by Streamlit directly).
    """
    title = viz_config.get("title", "")
    x = viz_config.get("x")
    y = viz_config.get("y")

    # Validate columns exist in df
    cols = df.columns.tolist()
    if x and x not in cols:
        x = cols[0] if cols else None
    if y and y not in cols:
        # Pick first numeric column
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        y = numeric_cols[0] if numeric_cols else (cols[1] if len(cols) > 1 else None)

    try:
        if viz_type == "bar":
            if not x or not y:
                return None
            fig = px.bar(df, x=x, y=y, title=title, color=x)
            fig.update_layout(showlegend=False)
            return fig

        elif viz_type == "line":
            if not x or not y:
                return None
            return px.line(df, x=x, y=y, title=title, markers=True)

        elif viz_type == "pie":
            names_col = x or cols[0]
            values_col = y or (df.select_dtypes(include="number").columns[0] if not df.select_dtypes(include="number").empty else cols[-1])
            return px.pie(df, names=names_col, values=values_col, title=title)

        elif viz_type == "scatter":
            if not x or not y:
                return None
            return px.scatter(df, x=x, y=y, title=title)

    except Exception:
        return None

    return None
