import importlib
import sys

import lib.log as log_module


def test_get_logger_cae_a_loguru_si_no_hay_logcentral(monkeypatch):
    monkeypatch.setitem(sys.modules, "logcentral_client", None)
    try:
        modulo = importlib.reload(log_module)
        logger = modulo.get_logger("pictohistorias")
        logger.info("mensaje de prueba {}", "ok")
    finally:
        monkeypatch.undo()
        importlib.reload(log_module)
