"""VPN-Pflicht (Notschalter): Abrufe nach außen nur, wenn der Tunnel sie wirklich trägt.

Reine Logik ohne Netzwerk, damit sie testbar ist. main.py hängt sie als Prüfung vor
jeden ausgehenden Abruf (make_iptv_client) und liest dafür /proc/net/route.

Warum die Routing-Tabelle und nicht „gibt es wg0?“: Beim Aufbau existiert das Interface
schon, bevor die Standard-Route auf den Tunnel zeigt; beim Abbau stellt SelfStream die
normale Route wieder her, damit der Container Internet behält. In beiden Momenten ginge
ein Abruf sonst direkt – mit der eigenen Adresse – zum Anbieter.
"""
import ipaddress

TUNNEL_PREFIXE = ("wg", "tun")
_RTF_UP = 0x1
_NULL = "00000000"
_HALB = "00000080"      # 128.0.0.0 in der Schreibweise von /proc/net/route (Little-Endian-Hex)


def _ist_tunnel(iface: str) -> bool:
    return iface.startswith(TUNNEL_PREFIXE)


def route_ueber_tunnel(proc_route: str) -> bool:
    """True, wenn Internet-Verkehr laut /proc/net/route durch den Tunnel geht.

    Zwei Formen gelten: die Standard-Route zeigt auf den Tunnel (WireGuard hier), oder
    beide Hälften 0.0.0.0/1 und 128.0.0.0/1 zeigen auf den Tunnel (OpenVPN
    „redirect-gateway def1“ – die normale Standard-Route bleibt dabei stehen, verliert
    aber gegen die genaueren Hälften).
    """
    standard = []          # Interfaces mit Standard-Route
    haelften = {}          # Ziel → Interface für die beiden /1-Routen
    for zeile in (proc_route or "").splitlines()[1:]:
        teile = zeile.split()
        if len(teile) < 8:
            continue
        iface, ziel, flags, maske = teile[0], teile[1].upper(), teile[3], teile[7].upper()
        try:
            if not int(flags, 16) & _RTF_UP:
                continue
        except ValueError:
            continue
        if ziel == _NULL and maske == _NULL:
            standard.append(iface)
        elif maske == _HALB and ziel in (_NULL, _HALB):
            haelften[ziel] = iface
    if len(haelften) == 2:
        return all(_ist_tunnel(i) for i in haelften.values())
    return bool(standard) and all(_ist_tunnel(i) for i in standard)


def ist_lan_ziel(host: str) -> bool:
    """True für Ziele im eigenen Netz (als IP angegeben) – die verlassen das Haus nicht.

    Namen werden bewusst NICHT aufgelöst: Die Namensauflösung selbst wäre schon eine
    Anfrage nach außen. Ein LAN-Dienst muss also als IP eingetragen sein.
    """
    h = (host or "").strip().strip("[]").lower()
    if h == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def gesperrt(pflicht: bool, tunnel_traegt: bool, host: str) -> bool:
    """True, wenn ein Abruf an ``host`` NICHT rausgehen darf."""
    if not pflicht or tunnel_traegt:
        return False
    return not ist_lan_ziel(host)
