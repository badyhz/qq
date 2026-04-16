"""
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigLoader:
    """"""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            self.config_path = Path(__file__).parent.parent / "config.yaml"
        else:
            self.config_path = Path(config_path)

        self.config: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f) or {}

        self._apply_env_overrides()
        self._set_defaults()

        return self.config

    def _apply_env_overrides(self) -> None:
        if 'QQ_MODE' in os.environ:
            self.config['mode'] = os.environ['QQ_MODE']

        if 'QQ_DATA_MODE' in os.environ:
            self.config['data_mode'] = os.environ['QQ_DATA_MODE']

        if 'QQ_LOOP_INTERVAL' in os.environ:
            if 'runtime' not in self.config:
                self.config['runtime'] = {}
            self.config['runtime']['loop_interval_seconds'] = float(os.environ['QQ_LOOP_INTERVAL'])

        if 'QQ_MAX_LOOPS' in os.environ:
            if 'runtime' not in self.config:
                self.config['runtime'] = {}
            self.config['runtime']['max_loops'] = int(os.environ['QQ_MAX_LOOPS'])

    def _set_defaults(self) -> None:
        if 'mode' not in self.config:
            self.config['mode'] = 'dry-run'

        if 'data_mode' not in self.config:
            self.config['data_mode'] = 'websocket'

        if 'runtime' not in self.config:
            self.config['runtime'] = {}

        runtime = self.config['runtime']
        runtime.setdefault('loop_interval_seconds', 1.0)
        runtime.setdefault('heartbeat_interval_seconds', 30)
        runtime.setdefault('max_loops', 0)

        if 'data' not in self.config:
            self.config['data'] = {}

        data = self.config['data']
        data.setdefault('warmup_candles', 100)
        data.setdefault('websocket_reconnect_seconds', 5)
        data.setdefault('websocket_stale_seconds', 60)

        if 'portfolio' not in self.config:
            self.config['portfolio'] = {}

        portfolio = self.config['portfolio']
        portfolio.setdefault('max_open_positions', 3)

        if 'logging' not in self.config:
            self.config['logging'] = {}

        logging_cfg = self.config['logging']
        logging_cfg.setdefault('level', 'INFO')
        logging_cfg.setdefault('file_path', 'logs/bot.log')

    def get(self, key: str, default: Any = None) -> Any:
        if not self.config:
            self.load()

        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def is_dry_run(self) -> bool:
        return self.get('mode', 'dry-run').lower() == 'dry-run'

    def is_live_mode(self) -> bool:
        return self.get('mode', 'dry-run').lower() == 'live'


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    loader = ConfigLoader(config_path)
    return loader.load()
