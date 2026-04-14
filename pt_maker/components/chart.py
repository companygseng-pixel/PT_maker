"""Native PPTX charts via python-pptx."""

from __future__ import annotations

from typing import Any

from pptx.chart.data import CategoryChartData, XyChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.util import Inches

from ..render.fonts import hex_to_rgb, resolve_color

_KIND_MAP = {
    "bar":    XL_CHART_TYPE.BAR_CLUSTERED,
    "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
    "line":   XL_CHART_TYPE.LINE,
    "pie":    XL_CHART_TYPE.PIE,
    "scatter": XL_CHART_TYPE.XY_SCATTER,
}


def add_chart(slide, block: dict[str, Any], theme: dict[str, Any]) -> None:
    chart_spec = block.get("chart", {})
    kind = _KIND_MAP.get(chart_spec.get("kind", "bar"), XL_CHART_TYPE.BAR_CLUSTERED)
    data = chart_spec.get("data", {}) or {}

    if kind == XL_CHART_TYPE.XY_SCATTER:
        cd = XyChartData()
        for series in data.get("series", []):
            s = cd.add_series(series.get("name", ""))
            for x, y in series.get("points", []):
                s.add_data_point(x, y)
    else:
        cd = CategoryChartData()
        cd.categories = data.get("categories", [])
        for series in data.get("series", []):
            cd.add_series(series.get("name", ""), series.get("values", []))

    chart_shape = slide.shapes.add_chart(
        kind,
        Inches(block["x_in"]), Inches(block["y_in"]),
        Inches(block["w_in"]), Inches(block["h_in"]),
        cd,
    )
    chart = chart_shape.chart
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False

    # Apply theme palette to series
    palette_hex = _theme_palette(theme)
    if kind != XL_CHART_TYPE.XY_SCATTER:
        for i, series in enumerate(chart.plots[0].series):
            color = hex_to_rgb(palette_hex[i % len(palette_hex)])
            fill = series.format.fill
            fill.solid()
            fill.fore_color.rgb = color

    # Axis titles (best-effort; not all chart types expose these)
    try:
        if chart_spec.get("x_title"):
            chart.category_axis.has_title = True
            chart.category_axis.axis_title.text_frame.text = chart_spec["x_title"]
        if chart_spec.get("y_title"):
            chart.value_axis.has_title = True
            chart.value_axis.axis_title.text_frame.text = chart_spec["y_title"]
    except Exception:
        pass


def _theme_palette(theme: dict[str, Any]) -> list[str]:
    colors = theme.get("colors", {})
    out = [colors.get("primary", "#0A3D62"), colors.get("secondary", "#60A3BC")]
    for a in colors.get("accent", []) or []:
        out.append(a)
    # Ensure a minimum of 5 distinct colors
    defaults = ["#0A3D62", "#60A3BC", "#F6B93B", "#EB2F06", "#38ADA9", "#6F1E51"]
    for d in defaults:
        if d not in out:
            out.append(d)
        if len(out) >= 6:
            break
    return out
