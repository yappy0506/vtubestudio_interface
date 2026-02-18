from vtsd.protocol import ProtocolError, validate_request


def test_validate_call_default_response_mode() -> None:
    req = validate_request({"op": "call", "messageType": "APIStateRequest"})
    assert req["responseMode"] == "data"


def test_validate_cast_ok() -> None:
    req = validate_request({"op": "cast", "messageType": "HotkeyTriggerRequest", "data": {"a": 1}})
    assert req["data"] == {"a": 1}


def test_validate_bad_op() -> None:
    try:
        validate_request({"op": "push", "messageType": "x"})
        assert False
    except ProtocolError:
        assert True
