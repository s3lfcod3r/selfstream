"""Charakterisierungs-Tests für den M3U-Parser (reine Funktionen, kein I/O)."""
import urllib.parse

from m3u_parser import parse_m3u, build_m3u


def test_parse_single_channel_with_attributes():
    content = (
        '#EXTM3U\n'
        '#EXTINF:-1 tvg-id="de.1" tvg-logo="http://logo/p.png" '
        'group-title="Sport",Channel One\n'
        'http://prov/stream/1\n'
    )
    chans = parse_m3u(content)
    assert len(chans) == 1
    ch = chans[0]
    assert ch["name"] == "Channel One"
    assert ch["url"] == "http://prov/stream/1"
    assert ch["group"] == "Sport"
    assert ch["tvg_id"] == "de.1"
    assert ch["tvg_logo"] == "http://logo/p.png"


def test_extgrp_used_when_no_group_title_attribute():
    content = (
        '#EXTM3U\n'
        '#EXTGRP:News\n'
        '#EXTINF:-1,N1\n'
        'http://prov/news\n'
    )
    chans = parse_m3u(content)
    assert len(chans) == 1
    assert chans[0]["group"] == "News"


def test_metadata_prefix_does_not_break_extinf():
    # #EXTVLCOPT etc. dürfen den vorherigen #EXTINF nicht verwerfen
    content = (
        '#EXTM3U\n'
        '#EXTINF:-1,Chan\n'
        '#EXTVLCOPT:http-user-agent=Foo\n'
        'http://prov/c\n'
    )
    chans = parse_m3u(content)
    assert len(chans) == 1
    assert chans[0]["name"] == "Chan"
    assert chans[0]["url"] == "http://prov/c"


def test_non_http_urls_are_skipped():
    content = (
        '#EXTM3U\n'
        '#EXTINF:-1,RTMP\n'
        'rtmp://prov/x\n'
    )
    assert parse_m3u(content) == []


def test_build_m3u_proxies_stream_urls():
    channels = [{
        "name": "C1", "stream_url": "http://p/1", "group_title": "Sport",
        "tvg_id": "de.1", "tvg_logo": "http://l.png", "tvg_rec": "0",
    }]
    out = build_m3u(channels, "http://proxy", "TKN")
    assert out.startswith("#EXTM3U")
    assert 'tvg-id="de.1"' in out
    assert 'group-title="Sport"' in out
    assert "http://proxy/iptv/TKN/stream?url=" in out
    assert urllib.parse.quote("http://p/1", safe="") in out


def test_build_m3u_adds_catchup_attrs_when_tvg_rec_positive():
    channels = [{
        "name": "C1", "stream_url": "http://p/1", "group_title": "G",
        "tvg_id": "de.1", "tvg_logo": "", "tvg_rec": "7",
    }]
    out = build_m3u(channels, "http://proxy", "TKN")
    assert 'catchup="shift"' in out
    assert 'catchup-days="7"' in out
