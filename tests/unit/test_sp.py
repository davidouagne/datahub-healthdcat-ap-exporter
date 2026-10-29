from pathlib import Path

import dh_healthdcat
from dh_healthdcat import sp

SRC = Path(dh_healthdcat.__file__).parent


def test_qualified_prefixes_local_name() -> None:
    assert sp.qualified("healthTheme") == sp.SP_PREFIX + "healthTheme"


def test_prefix_is_declared_only_in_sp_module() -> None:
    offenders = [
        path.relative_to(SRC).as_posix()
        for path in SRC.rglob("*.py")
        if path.name != "sp.py" and sp.SP_PREFIX in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
