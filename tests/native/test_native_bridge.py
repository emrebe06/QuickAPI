from quickapi.bridge import NativeBridge


def test_native_bridge_make_handler_can_be_monkeypatched():
    bridge = NativeBridge()

    def fake_call(library, symbol, payload):
        return {"library": library, "symbol": symbol, "payload": payload}

    bridge.call = fake_call
    handler = bridge.make_handler("libdemo.so", "score")

    assert handler({"x": 1}) == {"library": "libdemo.so", "symbol": "score", "payload": {"x": 1}}
