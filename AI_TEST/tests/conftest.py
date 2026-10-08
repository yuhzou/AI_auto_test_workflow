"""tests/conftest.py — 环境读取、脚本静态门禁与回放约定。

- `env(key)`：优先读系统环境变量，其次 tests/.env；
- pytest 收集阶段执行脚本静态门禁（script_guard），
  拒绝 TODO / 空实现 / 无断言 / skip-xfail 掩盖。
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = Path(__file__).with_name(".env")


def _load_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.is_file():
        return values
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_ENV = _load_env_file()


def env(key: str, default: str | None = None) -> str:
    """读取环境变量：系统环境 > tests/.env > 默认值。"""
    if key in os.environ:
        return os.environ[key]
    if key in _ENV:
        return _ENV[key]
    if default is not None:
        return default
    raise KeyError(f"环境变量 {key} 未配置：请在 tests/.env 中配置（参阅 .env.example）")


def pytest_collection_modifyitems(config, items) -> None:  # noqa: ARG001
    """收集阶段执行脚本静态门禁：未完成的脚本不得参与执行。"""
    guard_path = PROJECT_ROOT / ".agents/skills/shared/scripts/script_guard.py"
    if not guard_path.is_file():
        return
    spec = importlib.util.spec_from_file_location("_project_script_guard", guard_path)
    if spec is None or spec.loader is None:  # pragma: no cover
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    violations = module.run_guard([Path(__file__).parent])
    if violations:
        import pytest

        details = "\n".join(f"- {item['file']}: {item['message']}" for item in violations)
        raise pytest.UsageError(f"脚本静态门禁未通过（按探索流程逐条完成脚本）：\n{details}")
