"""Tests für m3u_parser.py (rein, stdlib)."""
import m3u_parser


def test_parse_m3u_simple():
    content = (
        "#EXTM3U\n"
        "#EXTINF:-1,Channel One\n"
        "http://example.com/live/one.m3u8\n"
        "#EXTINF:-1,Channel Two\n"
        "http://example.com/live/two.m3u8\n"
    )
    channels = m3u_parser.parse_m3u(content)
    assert len(channels) == 2
    assert channels[0]["name"] == "Channel One"
    assert channels[0]["url"] == "http://example.com/live/one.m3u8"
    assert channels[1]["name"] == "Channel Two"
    assert channels[1]["url"] == "http://example.com/live/two.m3u8"


def test_parse_m3u_group_title():
    content = (
        "#EXTM3U\n"
        '#EXTINF:-1 group-title="Sports",Sports Channel\n'
        "http://example.com/live/sports.m3u8\n"
    )
    channels = m3u_parser.parse_m3u(content)
    assert len(channels) == 1
    assert channels[0]["name"] == "Sports Channel"
    assert channels[0]["group"] == "Sports"


def test_parse_m3u_name_with_comma_preserved():
    # Name mit Komma: getrennt wird nur am ERSTEN Komma außerhalb der
    # Anführungszeichen; das Komma im Namen bleibt erhalten.
    content = (
        "#EXTM3U\n"
        "#EXTINF:-1,RTL, aber anders\n"
        "http://example.com/live/rtl.m3u8\n"
    )
    channels = m3u_parser.parse_m3u(content)
    assert len(channels) == 1
    assert channels[0]["name"] == "RTL, aber anders"


def test_parse_m3u_attr_value_with_comma():
    # Komma in einem Attribut-Wert (in Anführungszeichen) zerlegt nicht die
    # Attribute; der Name folgt erst nach dem Komma außerhalb der Anführungszeichen.
    content = (
        "#EXTM3U\n"
        '#EXTINF:-1 tvg-name="A, B",Channel\n'
        "http://example.com/live/ch.m3u8\n"
    )
    channels = m3u_parser.parse_m3u(content)
    assert len(channels) == 1
    assert channels[0]["name"] == "Channel"
    assert channels[0]["tvg_name"] == "A, B"


def test_parse_m3u_tvg_id_and_logo():
    content = (
        "#EXTM3U\n"
        '#EXTINF:-1 tvg-id="abc123" tvg-logo="http://example.com/l.png",'
        "News Channel\n"
        "http://example.com/live/news.m3u8\n"
    )
    channels = m3u_parser.parse_m3u(content)
    assert len(channels) == 1
    assert channels[0]["tvg_id"] == "abc123"
    assert channels[0]["tvg_logo"] == "http://example.com/l.png"
    assert channels[0]["name"] == "News Channel"


def test_parse_m3u_non_http_url_skipped():
    # Nicht-HTTP-Zeilen werden übersprungen (nur http/https werden als URL genommen).
    content = (
        "#EXTM3U\n"
        "#EXTINF:-1,Channel One\n"
        "http://example.com/live/one.m3u8\n"
        "#EXTINF:-1,Channel Two\n"
        "rtsp://example.com/live/two\n"
    )
    channels = m3u_parser.parse_m3u(content)
    assert len(channels) == 1
    assert channels[0]["url"] == "http://example.com/live/one.m3u8"


def test_parse_m3u_empty():
    assert m3u_parser.parse_m3u("") == []


def test_parse_m3u_only_header():
    assert m3u_parser.parse_m3u("#EXTM3U\n") == []


def test_build_m3u_escapes_quotes_in_attrs():
    # Anführungszeichen in Attributwerten werden zu &quot; umgeschrieben,
    # damit sie die Attributliste nicht zerlegen.
    channels = [
        {
            "name": "Chan",
            "url": "http://example.com/live.x",
            "group": 'Gr"uppe',
            "tvg_id": "x",
            "tvg_logo": "",
            "tvg_name": "",
            "tvg_rec": "0",
            "stable_uid": "",
            "stream_url": "http://example.com/live.x",
        }
    ]
    out = m3u_parser.build_m3u(channels, "http://p:8000", "tok")
    assert "&quot;" in out


def test_build_m3u_strips_newlines_in_name():
    channels = [
        {
            "name": "Chan\nName",
            "url": "http://example.com/live.x",
            "group": "",
            "tvg_id": "",
            "tvg_logo": "",
            "tvg_name": "",
            "tvg_rec": "0",
            "stable_uid": "",
            "stream_url": "http://example.com/live.x",
        }
    ]
    out = m3u_parser.build_m3u(channels, "http://p:8000", "tok")
    assert "\nChan" not in out
    assert "ChanName" in out


def test_build_m3u_catchup_attrs():
    channels = [
        {
            "name": "Chan",
            "url": "http://example.com/live.x",
            "group": "",
            "tvg_id": "vid",
            "tvg_logo": "",
            "tvg_name": "",
            "tvg_rec": "7",
            "stable_uid": "",
            "stream_url": "http://example.com/live.x",
        }
    ]
    out = m3u_parser.build_m3u(channels, "http://p:8000", "tok")
    assert 'catchup-days="7"' in out
    assert "catchup-source=" in out
    assert 'catchup="shift"' in out


def test_build_m3u_stable_uid_used():
    channels = [
        {
            "name": "Chan",
            "url": "http://example.com/live.x",
            "group": "",
            "tvg_id": "",
            "tvg_logo": "",
            "tvg_name": "",
            "tvg_rec": "0",
            "stable_uid": "uid-42",
        }
    ]
    out = m3u_parser.build_m3u(channels, "http://p:8000", "tok")
    assert "/live/uid-42" in out


def test_build_m3u_legacy_url_used_without_uid():
    channels = [
        {
            "name": "Chan",
            "url": "http://example.com/live.x",
            "group": "",
            "tvg_id": "",
            "tvg_logo": "",
            "tvg_name": "",
            "tvg_rec": "0",
            "stable_uid": "",
            "stream_url": "http://example.com/live.x",
        }
    ]
    out = m3u_parser.build_m3u(channels, "http://p:8000", "tok")
    assert "/stream?url=" in out
