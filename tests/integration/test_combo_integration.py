"""Opt-in read-only contract check. No test posts revenue to a provider account."""

import os

import pytest

from adapters.combo.client import ComboClient


@pytest.mark.live
async def test_combo_locations():
    token = os.environ.get("COMBO_TEST_API_KEY")
    if not token:
        pytest.skip("Set COMBO_TEST_API_KEY for a dedicated test account")
    async with ComboClient(token) as combo:
        assert isinstance(await combo.get_locations(), list)
