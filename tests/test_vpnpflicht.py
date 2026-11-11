"""Tests für die VPN-Pflicht (vpnpflicht.py)."""
import vpnpflicht as v

KOPF = "Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT\n"


def _tab(*zeilen):
    return KOPF + "".join(z + "\n" for z in zeilen)


LAN = "eth0\t0001A8C0\t00000000\t0001\t0\t0\t0\t00FFFFFF\t0\t0\t0"
ENDPUNKT = "eth0\t03F04E93\t0101A8C0\t0007\t0\t0\t0\tFFFFFFFF\t0\t0\t0"
STD_WG = "wg0\t00000000\t00000000\t0001\t0\t0\t0\t00000000\t0\t0\t0"
STD_ETH = "eth0\t00000000\t0101A8C0\t0003\t0\t0\t0\t00000000\t0\t0\t0"
HALB1_TUN = "tun0\t00000000\t0100080A\t0003\t0\t0\t0\t00000080\t0\t0\t0"
HALB2_TUN = "tun0\t00000080\t0100080A\t0003\t0\t0\t0\t00000080\t0\t0\t0"


# ── Trägt der Tunnel den Verkehr? ───────────────────────────────────────────

def test_wireguard_laeuft():
    # So sieht die Tabelle im laufenden Container aus (11.11.2026).
    assert v.route_ueber_tunnel(_tab(STD_WG, ENDPUNKT, LAN))


def test_tunnel_abgebaut_normale_route_zurueck():
    assert not v.route_ueber_tunnel(_tab(STD_ETH, LAN))


def test_aufbau_interface_da_aber_route_noch_nicht():
    # wg0 existiert schon (LAN-Zeile egal), Standard-Route zeigt noch auf eth0.
    assert not v.route_ueber_tunnel(_tab(STD_ETH, ENDPUNKT, LAN))


def test_keine_standard_route():
    assert not v.route_ueber_tunnel(_tab(LAN))
    assert not v.route_ueber_tunnel("")
    assert not v.route_ueber_tunnel(None)


def test_openvpn_def1_haelften_gewinnen():
    assert v.route_ueber_tunnel(_tab(STD_ETH, HALB1_TUN, HALB2_TUN, LAN))


def test_openvpn_nur_eine_haelfte_reicht_nicht():
    assert not v.route_ueber_tunnel(_tab(STD_ETH, HALB1_TUN, LAN))


def test_zwei_standard_routen_eine_am_tunnel_vorbei():
    assert not v.route_ueber_tunnel(_tab(STD_WG, STD_ETH, LAN))


def test_route_ohne_up_flag_zaehlt_nicht():
    aus = "wg0\t00000000\t00000000\t0000\t0\t0\t0\t00000000\t0\t0\t0"
    assert not v.route_ueber_tunnel(_tab(aus, LAN))


# ── LAN-Ziele ───────────────────────────────────────────────────────────────

def test_lan_ziele():
    for h in ("192.168.1.2", "10.0.0.5", "172.16.3.4", "127.0.0.1", "localhost", "[::1]"):
        assert v.ist_lan_ziel(h), h


def test_aussen_ziele_und_namen():
    for h in ("8.8.8.8", "example.com", "nas.local", "", None):
        assert not v.ist_lan_ziel(h), h


# ── Die Entscheidung ────────────────────────────────────────────────────────

def test_ohne_pflicht_nie_gesperrt():
    assert not v.gesperrt(False, False, "example.com")


def test_pflicht_und_tunnel_traegt():
    assert not v.gesperrt(True, True, "example.com")


def test_pflicht_ohne_tunnel_sperrt_aussen():
    assert v.gesperrt(True, False, "example.com")
    assert v.gesperrt(True, False, "8.8.8.8")


def test_pflicht_ohne_tunnel_laesst_lan_durch():
    assert not v.gesperrt(True, False, "192.168.1.2")
