from __future__ import annotations

import os
from pathlib import Path


os.environ["WASTE_DSS_DEMO_MODE"] = "1"

app_path = Path(__file__).with_name("app.py")
exec(compile(app_path.read_text(encoding="utf-8"), str(app_path), "exec"))
