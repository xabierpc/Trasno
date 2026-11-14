from __future__ import annotations

from datetime import date

import pytest

from core.herramientas import validar
from modules.tracking.application.casos_uso import CasosUsoTracking
from modules.tracking.application.herramientas import herramientas_tracking
from modules.tracking.domain.errores import MetricaNoEncontrada, TipoIncorrecto
from modules.tracking.domain.metricas import TipoMetrica

HOY = date(2026, 11, 14)


def test_registrar_ver_y_listar(casos: CasosUsoTracking):
    casos.crear_metrica("peso", "kg", TipoMetrica.NUMERICA)
    casos.crear_metrica("ánimo", "", TipoMetrica.ESCALA, escala_max=10)
    h = {t.nombre: validar(t) for t in herramientas_tracking(casos)}
    assert all(not t.requiere_confirmacion for t in h.values())
    assert h["registrar_metrica"].sensible

    registrar, ver = h["registrar_metrica"].funcion, h["ver_metrica"].funcion
    assert registrar("peso", 74.3, HOY) == "Guardado: peso = 74.3 el 14/11/2026."
    assert ver("peso", HOY, HOY) == "- 14/11/2026: 74.3"
    assert ver("peso", date(2026, 1, 1), date(2026, 1, 2)).startswith("No hay valores")
    assert h["metricas"].funcion() == "- peso: numerica en kg\n- ánimo: escala (1-10)"


def test_los_errores_del_dominio_llegan_al_agente(casos: CasosUsoTracking):
    casos.crear_metrica("pasos", "", TipoMetrica.CONTEO)
    registrar = {t.nombre: t.funcion for t in herramientas_tracking(casos)}["registrar_metrica"]
    with pytest.raises(MetricaNoEncontrada):
        registrar("peso", 74.3, HOY)
    with pytest.raises(TipoIncorrecto):
        registrar("pasos", "muchos", HOY)
