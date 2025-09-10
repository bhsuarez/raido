from typing import Dict, Any, List, Optional, Tuple

from app.services.liquidsoap_client import LiquidsoapClient


def test_split_metadata_string_respects_quotes():
    cli = LiquidsoapClient(host="localhost", port=0)
    s = 'artist="AC/DC",title="Rock, Roll",status=playing'
    parts = cli._split_metadata_string(s)
    assert parts == ['artist="AC/DC"', 'title="Rock, Roll"', 'status=playing']


def test_parse_metadata_response_handles_multiline_and_single():
    cli = LiquidsoapClient(host="localhost", port=0)

    single = 'artist="AC/DC", title="Thunderstruck", status=playing'
    out = cli._parse_metadata_response(single)
    assert out["artist"] == "AC/DC"
    assert out["title"] == "Thunderstruck"
    assert out["status"] == "playing"

    multi = """
artist="Daft Punk"
title="Harder Better Faster Stronger"
status=ready
END
""".strip()
    out2 = cli._parse_metadata_response(multi)
    assert out2["artist"] == "Daft Punk"
    assert out2["status"] == "ready"


class FakeClient(LiquidsoapClient):
    def __init__(self, mapping: Dict[int, Dict[str, Any]], order: List[int]):
        super().__init__(host="localhost", port=0)
        self._map = mapping
        self._order = order

    def list_request_ids(self) -> List[int]:  # type: ignore[override]
        return list(self._order)

    def get_request_metadata(self, rid: int) -> Dict[str, Any]:  # type: ignore[override]
        return dict(self._map.get(rid, {}))


def test_get_current_and_next_ready_rid_selection():
    mapping = {
        101: {"status": "buffering"},
        102: {"status": "playing"},
        103: {"status": "ready"},
        104: {"status": "queued"},
    }
    order = [101, 102, 103, 104]
    cli: FakeClient = FakeClient(mapping, order)
    current, nxt = cli.get_current_and_next_ready_rid()
    assert current == 102
    assert nxt == 103

