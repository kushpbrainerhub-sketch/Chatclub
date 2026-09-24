"""
End-to-end tests: two fake browsers talk to the real /ws endpoint.
"""

from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


def profile(name, gender, age=25, country="IN"):
    return {"username": name, "age": age, "country": country, "gender": gender}


def receive(ws):
    """Next event, skipping the online_count broadcasts."""
    while True:
        data = ws.receive_json()
        if data["type"] != "online_count":
            return data


def setup_function():
    # Fresh state for every test.
    main.connections.clear()
    main.matcher = main.Matcher()


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_two_users_match_and_chat():
    with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as b:
        a.send_json({"type": "join", "profile": profile("Kush", "male")})
        assert receive(a) == {"type": "waiting"}

        b.send_json({"type": "join", "profile": profile("Riya", "female", 21)})
        matched_b = receive(b)
        matched_a = receive(a)
        assert matched_b["partner"]["username"] == "Kush"
        assert matched_a["partner"]["username"] == "Riya"

        a.send_json({"type": "message", "text": "  hello!  "})
        assert receive(b) == {"type": "message", "text": "hello!", "from": "partner"}

        b.send_json({"type": "typing"})
        assert receive(a) == {"type": "partner_typing"}

        b.send_json({"type": "leave"})
        assert receive(a) == {"type": "partner_left"}


def test_underage_join_gets_error():
    with client.websocket_connect("/ws") as a:
        a.send_json({"type": "join", "profile": profile("Kid", "male", age=17)})
        event = receive(a)
        assert event["type"] == "error"
        assert "18" in event["message"]


def test_disconnect_tells_partner():
    with client.websocket_connect("/ws") as a:
        with client.websocket_connect("/ws") as b:
            a.send_json({"type": "join", "profile": profile("Kush", "male")})
            receive(a)
            b.send_json({"type": "join", "profile": profile("Riya", "female")})
            receive(a)
            receive(b)
        # b's socket is now closed
        assert receive(a) == {"type": "partner_left"}


def test_message_rate_limit():
    with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as b:
        a.send_json({"type": "join", "profile": profile("Kush", "male")})
        receive(a)
        b.send_json({"type": "join", "profile": profile("Riya", "female")})
        receive(a)
        receive(b)
        for i in range(6):
            a.send_json({"type": "message", "text": f"msg {i}"})
        for i in range(5):
            assert receive(b)["text"] == f"msg {i}"
        assert receive(a)["type"] == "error"  # the 6th was blocked


def test_bad_words_are_censored():
    with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as b:
        a.send_json({"type": "join", "profile": profile("Kush", "male")})
        receive(a)
        b.send_json({"type": "join", "profile": profile("Riya", "female")})
        receive(a)
        receive(b)
        a.send_json({"type": "message", "text": "oh shit sorry"})
        assert receive(b)["text"] == "oh *** sorry"
