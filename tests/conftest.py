# tests/conftest.py
#
# Добавляет корень проекта и пакет core/ в sys.path,
# чтобы тесты могли импортировать модули без изменения самих тест-файлов.
# Работает автоматически при запуске pytest из любой директории.

import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CORE = os.path.join(_ROOT, "core")

for path in (_ROOT, _CORE):
    if path not in sys.path:
        sys.path.insert(0, path)
