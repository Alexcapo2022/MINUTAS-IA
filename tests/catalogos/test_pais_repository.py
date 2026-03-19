# tests/catalogos/test_pais_repository.py
"""
Unit tests puros para PaisRepository.find_by_name_or_gentilicio.
No requieren BD real — usa un mock de Session y un mock de Pais.
Ejecutar: python -m pytest tests/catalogos/test_pais_repository.py -v
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from unittest.mock import MagicMock
from app.repositories.catalogos_repository import PaisRepository


# ── Helper: crea un objeto Pais mock ─────────────────────────────────────────

def make_pais_row(co_pais: int, no_pais: str, gerundio_pais: str) -> MagicMock:
    row = MagicMock()
    row.co_pais = co_pais
    row.no_pais = no_pais
    row.gerundio_pais = gerundio_pais
    row.in_estado = 1
    return row


def make_repo(first_result_no_pais=None, first_result_gerundio=None) -> PaisRepository:
    """
    Crea un PaisRepository con una sesión mockeada.
    - first_result_no_pais: fila que retorna la query por no_pais (o None)
    - first_result_gerundio: fila que retorna la query por gerundio_pais (o None)
    """
    db = MagicMock()

    call_count = {"n": 0}

    def scalars_side_effect():
        call_count["n"] += 1
        mock_scalars = MagicMock()
        if call_count["n"] == 1:
            mock_scalars.first.return_value = first_result_no_pais
        else:
            mock_scalars.first.return_value = first_result_gerundio
        return mock_scalars

    db.execute.return_value.scalars.side_effect = scalars_side_effect
    return PaisRepository(db)


# ── Tests ────────────────────────────────────────────────────────────────────

class TestFindByNameOrGentilicio:

    def test_match_por_no_pais(self):
        """Si 'SUIZA' existe en no_pais, matchea en primer intento; matched_by_gerundio=False."""
        row = make_pais_row(co_pais=756, no_pais="SUIZA", gerundio_pais="SUIZO")
        repo = make_repo(first_result_no_pais=row)

        result, matched = repo.find_by_name_or_gentilicio("SUIZA")

        assert result is row
        assert matched is False

    def test_match_por_gerundio(self):
        """Si 'SUIZO' no está en no_pais pero sí en gerundio_pais, matched_by_gerundio=True."""
        row = make_pais_row(co_pais=756, no_pais="SUIZA", gerundio_pais="SUIZO")
        repo = make_repo(first_result_no_pais=None, first_result_gerundio=row)

        result, matched = repo.find_by_name_or_gentilicio("SUIZO")

        assert result is row
        assert matched is True

    def test_no_match_ninguno(self):
        """Si no existe en ninguna columna, retorna (None, False)."""
        repo = make_repo(first_result_no_pais=None, first_result_gerundio=None)

        result, matched = repo.find_by_name_or_gentilicio("MARTEANO")

        assert result is None
        assert matched is False

    def test_vacio_retorna_none_false(self):
        """Nombre vacío → (None, False) sin hacer queries."""
        db = MagicMock()
        repo = PaisRepository(db)

        result, matched = repo.find_by_name_or_gentilicio("")
        assert result is None
        assert matched is False
        db.execute.assert_not_called()

    def test_none_retorna_none_false(self):
        """Nombre None → (None, False) sin hacer queries."""
        db = MagicMock()
        repo = PaisRepository(db)

        result, matched = repo.find_by_name_or_gentilicio(None)
        assert result is None
        assert matched is False
        db.execute.assert_not_called()

    def test_find_by_name_alias_retorna_solo_row(self):
        """find_by_name (alias backward-compat) retorna solo la fila, sin el flag."""
        row = make_pais_row(co_pais=51, no_pais="PERU", gerundio_pais="PERUANO")
        repo = make_repo(first_result_no_pais=row)

        result = repo.find_by_name("PERU")
        assert result is row

    def test_case_insensitive_normalizado(self):
        """El input en minúsculas o mixto debe normalizarse y matchear."""
        row = make_pais_row(co_pais=380, no_pais="ITALIA", gerundio_pais="ITALIANO")
        # el primer intento (no_pais) retorna None, el segundo (gerundio) el row
        repo = make_repo(first_result_no_pais=None, first_result_gerundio=row)

        result, matched = repo.find_by_name_or_gentilicio("Italiano")
        assert result is row
        assert matched is True


class TestGerundioAplicadoEnParticipante:
    """
    Prueba de integración ligera: verifica la lógica de asignación de pais/gerundio
    tal como ocurre en _resolve_catalogs_and_ciiu de participante.py.
    """

    def _simular_resolucion(self, pais_input: str, row, matched_by_gerundio: bool):
        """Simula la lógica del bloque de catálogo de país en participante.py."""
        pais = pais_input
        co_pais = None

        if row:
            co_pais = getattr(row, "co_pais", None)
            if matched_by_gerundio:
                gerundio = (getattr(row, "gerundio_pais", None) or "").strip().upper()
                if gerundio:
                    pais = gerundio

        return pais, co_pais

    def test_gentilicio_suizo_resuelve_co_pais_y_mantiene_gerundio(self):
        """LLM manda 'SUIZO' → co_pais resuelto, pais='SUIZO' (gerundio de BD)."""
        row = make_pais_row(co_pais=756, no_pais="SUIZA", gerundio_pais="SUIZO")
        pais, co_pais = self._simular_resolucion("SUIZO", row, matched_by_gerundio=True)
        assert co_pais == 756
        assert pais == "SUIZO"

    def test_nombre_oficial_resuelve_co_pais_sin_cambiar_pais(self):
        """LLM manda 'SUIZA' → co_pais resuelto, pais='SUIZA' (sin cambiar)."""
        row = make_pais_row(co_pais=756, no_pais="SUIZA", gerundio_pais="SUIZO")
        pais, co_pais = self._simular_resolucion("SUIZA", row, matched_by_gerundio=False)
        assert co_pais == 756
        assert pais == "SUIZA"  # no cambia al gerundio

    def test_no_match_deja_co_pais_null(self):
        """Sin match → co_pais=None, pais igual al input."""
        pais, co_pais = self._simular_resolucion("MARTEANO", None, matched_by_gerundio=False)
        assert co_pais is None
        assert pais == "MARTEANO"
