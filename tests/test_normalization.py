from __future__ import annotations

from src.utils.normalization import normalize_sticker_code


def test_normalize_sticker_code():
    assert normalize_sticker_code("MEX-12") == "MEX12"
    assert normalize_sticker_code("mex 12") == "MEX12"
    assert normalize_sticker_code("FWC1") == "FWC1"
    assert normalize_sticker_code("00") == "00"

