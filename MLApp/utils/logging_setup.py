from pathlib import Path
import logging, sys, warnings, faulthandler
from logging.handlers import RotatingFileHandler

# logs/ under project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"
CRASH_FILE = LOG_DIR / "crash.log"

# capture hard crashes (segfaults, etc.)
_crash_fp = open(CRASH_FILE, "a", buffering=1, encoding="utf-8")
faulthandler.enable(_crash_fp)

def setup_logging(level=logging.DEBUG):
    root = logging.getLogger()
    root.setLevel(level)

    # clear existing handlers
    for h in list(root.handlers):
        root.removeHandler(h)

    fh = RotatingFileHandler(
        LOG_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    root.addHandler(fh)

    # pipe warnings → logging
    logging.captureWarnings(True)

    # catch uncaught exceptions → file
    def _excepthook(exc_type, exc, tb):
        logging.getLogger("UNCAUGHT").exception(
            "Uncaught exception", exc_info=(exc_type, exc, tb)
        )
    sys.excepthook = _excepthook

    return root

def get_logger(name="app"):
    return logging.getLogger(name)
