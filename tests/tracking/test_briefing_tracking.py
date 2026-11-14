from __future__ import annotations

from datetime import date, timedelta

from modules.tracking.application.briefing import SeccionBriefingTracking, cuando, numero
from modules.tracking.application.casos_uso import CasosUsoTracking
from modules.tracking.domain.metricas import TipoMetrica

HOY = date(2026, 11, 14)


def hace(dias: int) -> date:
    return HOY - timedelta(days=dias)


def test_numero_y_cuando():
    assert (numero(74.3), numero(75.0), numero(74.25)) == ("74,3", "75", "74,2")
    assert (cuando(HOY, HOY), cuando(hace(1), HOY), cuando(hace(3), HOY)) == (
        "hoy",
        "ayer",
        "el 11/11",
    )


def test_ultimo_peso_y_media_de_la_semana(casos: CasosUsoTracking):
    casos.crear_metrica("peso", "kg", TipoMetrica.NUMERICA)
    casos.registrar_metrica("peso", 75.0, hace(20))  # fuera de la semana
    casos.registrar_metrica("peso", 74.6, hace(3))
    casos.registrar_metrica("peso", 74.0, hace(1))

    assert SeccionBriefingTracking(casos).lineas(HOY) == [
        "Peso: **74 kg** (ayer) · media de 7 días 74,3 kg"
    ]


def test_sin_peso_ni_metrica_no_dice_nada(casos: CasosUsoTracking):
    assert SeccionBriefingTracking(casos).lineas(HOY) == []
    casos.crear_metrica("peso", "kg", TipoMetrica.NUMERICA)
    assert SeccionBriefingTracking(casos).lineas(HOY) == []


def test_rachas_de_habitos_desde_dos_dias(casos: CasosUsoTracking):
    casos.crear_metrica("leer", "", TipoMetrica.BOOLEANA)
    casos.crear_metrica("meditar", "", TipoMetrica.BOOLEANA)
    casos.crear_metrica("estirar", "", TipoMetrica.BOOLEANA, activa=False)
    for dias in (1, 2, 3):
        casos.registrar_metrica("leer", True, hace(dias))
        casos.registrar_metrica("estirar", True, hace(dias))
    casos.registrar_metrica("meditar", True, hace(1))  # racha de 1: no se menciona

    assert SeccionBriefingTracking(casos).lineas(HOY) == ["Racha de leer: 3 días"]
