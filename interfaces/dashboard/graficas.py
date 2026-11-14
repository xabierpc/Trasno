"""Gráficas compartidas por las páginas del dashboard (solo presentación)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import pandas as pd
import plotly.graph_objects as go


def grafica_con_media_movil(
    puntos: Sequence[tuple[date, float]], nombre: str, unidad: str, ventana_dias: int = 7
) -> go.Figure:
    """Valores diarios como puntos y su media móvil de `ventana_dias` días como línea."""
    serie = pd.Series(
        [valor for _, valor in puntos],
        index=pd.DatetimeIndex([dia for dia, _ in puntos]),
        dtype="float64",
    ).sort_index()
    # Ventana por tiempo, no por número de filas: los días sin registro no la alargan.
    media = serie.rolling(f"{ventana_dias}D").mean()
    figura = go.Figure()
    figura.add_scatter(x=serie.index, y=serie, mode="markers", name=nombre)
    figura.add_scatter(x=media.index, y=media, mode="lines", name=f"Media {ventana_dias} días")
    figura.update_layout(yaxis_title=unidad, hovermode="x unified", margin={"t": 20})
    return figura
