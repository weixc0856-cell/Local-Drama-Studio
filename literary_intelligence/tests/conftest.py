from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CORPUS = ROOT / "literary_intelligence" / "tests" / "fixtures" / "corpus_short"

SOURCE_ID = "src_test_short"
WORK = "测试短文本"
AUTHOR = "测试作者"
EDITION = "测试版本"
TARGET_LOCATOR = "测试文本/首句/第1句"
CONTEXT_LOCATOR = "测试文本/首句/第2句"
TARGET_QUOTE = "白日依山尽"
TARGET_SOURCE_QUOTE = "白日依山盡"
