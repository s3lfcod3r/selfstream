# Security Policy

🇬🇧 English &nbsp;|&nbsp; 🇩🇪 [Deutsch](#deutsch)

## Supported Versions

Security fixes are provided for the current release line only.

| Version | Supported |
|---------|-----------|
| 1.8x (current release line) | ✅ |
| everything older | ❌ |

Always run the latest image (`ghcr.io/s3lfcod3r/selfstream:latest`) to receive security updates.

## Reporting a Vulnerability

Please report security issues **privately** — do not open a public GitHub issue for a vulnerability.

- **Email:** info@selfcoder.de
- Include: affected version, a description of the issue, and steps to reproduce (a proof of concept helps).
- You will receive an acknowledgement as soon as possible. We aim to confirm the report and discuss a fix or mitigation timeline with you.

Please give us a reasonable window to ship a fix before any public disclosure (coordinated/responsible disclosure).

## Scope

selfstream is intended to run on a trusted home/lab network. The admin panel (port 8080) should **not** be exposed directly to the internet. Issues that require an already-compromised LAN or direct internet exposure of the admin panel are considered out of the normal threat model, but we still welcome reports.

### Known limitations (open, as of v1.83)

- **The container runs as `root`** and needs `CAP_NET_ADMIN` plus `/dev/net/tun` to bring up the WireGuard/OpenVPN tunnel. The root filesystem is not read-only. Dropping privileges is not a one-line change (the tunnel setup needs them) and requires VPN testing, so it is tracked as an open item rather than shipped untested.
- **During setup over plain HTTP in the LAN** the new admin token travels unencrypted. That is accepted within the threat model above, but you should be aware of it — set the token on a network you trust.

---

<a name="deutsch"></a>

# Sicherheitsrichtlinie

## Unterstützte Versionen

Sicherheits-Updates gibt es nur für die aktuelle Release-Linie.

| Version | Unterstützt |
|---------|-------------|
| 1.8x (aktuelle Release-Linie) | ✅ |
| alles Ältere | ❌ |

Bitte immer das aktuelle Image (`ghcr.io/s3lfcod3r/selfstream:latest`) verwenden.

### Bekannte Einschränkungen (offen, Stand v1.83)

- **Der Container läuft als `root`** und braucht `CAP_NET_ADMIN` sowie `/dev/net/tun` für den WireGuard-/OpenVPN-Tunnel. Das Root-Dateisystem ist nicht schreibgeschützt. Die Rechte abzulegen ist kein Einzeiler (der Tunnelaufbau braucht sie) und muss mit echten VPN-Tests abgesichert werden — deshalb steht es hier als offener Punkt statt ungetestet im Release.
- **Bei der Einrichtung über reines HTTP im LAN** geht das neue Admin-Token im Klartext über das Netz. Im oben beschriebenen Bedrohungsmodell ist das akzeptiert, sollte aber bekannt sein: Token nur in einem vertrauenswürdigen Netz setzen.

## Sicherheitslücke melden

Sicherheitsprobleme bitte **vertraulich** melden — kein öffentliches GitHub-Issue für eine Schwachstelle anlegen.

- **E-Mail:** info@selfcoder.de
- Bitte angeben: betroffene Version, Beschreibung des Problems, Schritte zur Reproduktion (ein Proof of Concept hilft).
- Du erhältst so schnell wie möglich eine Eingangsbestätigung. Wir bestätigen die Meldung und stimmen einen Zeitplan für Fix/Mitigation mit dir ab.

Bitte gib uns vor einer Veröffentlichung ausreichend Zeit für einen Fix (koordinierte/verantwortliche Offenlegung).

## Geltungsbereich

selfstream ist für den Betrieb in einem vertrauenswürdigen Heim-/Lab-Netzwerk gedacht. Das Admin-Panel (Port 8080) sollte **nicht** direkt aus dem Internet erreichbar sein. Probleme, die ein bereits kompromittiertes LAN oder ein direkt aus dem Internet erreichbares Admin-Panel voraussetzen, liegen außerhalb des normalen Bedrohungsmodells — Meldungen sind aber trotzdem willkommen.
