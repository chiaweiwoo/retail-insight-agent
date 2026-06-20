from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Outcome persistence is integration-heavy and is deferred for the v2 checkpoint.")
