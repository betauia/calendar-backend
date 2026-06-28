from importlib.resources import path

import yaml

import logging.handlers
from pathlib import Path

from Domain.ProvidersConfig import ProvidersConfig


class ConfigService:
    def load_config_from_file(self, config_path: Path) -> ProvidersConfig:        
        with config_path.open() as f:
            data = yaml.safe_load(f)
        
        return ProvidersConfig(**data)
    

    def setup_logging(self, log_dir: str = "logs", level: int = logging.DEBUG) -> logging.Logger:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        logger = logging.getLogger("betacalendar")
        logger.setLevel(logging.DEBUG)  # capture everything, handlers filter

        # --- Formatters ---
        console_formatter = logging.Formatter(
            "%(levelname)-8s %(message)s"
        )
        file_formatter = logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # --- Console handler ---
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)

        # --- File handler ---
        file_handler = logging.handlers.RotatingFileHandler(
            log_path / "betacalendar.log",
            maxBytes=1_000_000,   # 1MB per file
            backupCount=5,        # keep 5 rotated files
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger