# Security Policy

🇬🇧 English &nbsp;|&nbsp; 🇩🇪 [Deutsch](#deutsch)

## Supported Versions

Security fixes are provided for the latest release line only.

| Version | Supported |
|---------|-----------|
| 1.1.x   | ✅ |
| < 1.1   | ❌ |

Always run the latest image (`ghcr.io/s3lfcod3r/selfstream:latest`) to receive security updates.

## Reporting a Vulnerability

Please report security issues **privately** — do not open a public GitHub issue for a vulnerability.

- **Email:** info@selfcoder.de
- Include: affected version, a description of the issue, and steps to reproduce (a proof of concept helps).
- You will receive an acknowledgement as soon as possible. We aim to confirm the report and discuss a fix or mitigation timeline with you.

Please give us a reasonable window to ship a fix before any public disclosure (coordinated/responsible disclosure).

## Scope

selfstream is intended to run on a trusted home/lab network. The admin panel (port 8080) should **not** be exposed directly to the internet. Issues that require an already-compromised LAN or direct internet exposure of the admin panel are considered out of the normal threat model, but we still welcome reports.

---

<a name="deutsch"></a>

# Sicherheitsrichtlinie

## Unterstützte Versionen

Sicherheits-Updates gibt es nur für die aktuelle Release-Linie.

| Version | Unterstützt |
|---------|-------------|
| 1.1.x   | ✅ |
| < 1.1   | ❌ |

Bitte immer das aktuelle Image (`ghcr.io/s3lfcod3r/selfstream:latest`) verwenden.

## Sicherheitslücke melden

Sicherheitsprobleme bitte **vertraulich** melden — kein öffentliches GitHub-Issue für eine Schwachstelle anlegen.

- **E-Mail:** info@selfcoder.de
- Bitte angeben: betroffene Version, Beschreibung des Problems, Schritte zur Reproduktion (ein Proof of Concept hilft).
- Du erhältst so schnell wie möglich eine Eingangsbestätigung. Wir bestätigen die Meldung und stimmen einen Zeitplan für Fix/Mitigation mit dir ab.

Bitte gib uns vor einer Veröffentlichung ausreichend Zeit für einen Fix (koordinierte/verantwortliche Offenlegung).

## Geltungsbereich

selfstream ist für den Betrieb in einem vertrauenswürdigen Heim-/Lab-Netzwerk gedacht. Das Admin-Panel (Port 8080) sollte **nicht** direkt aus dem Internet erreichbar sein. Probleme, die ein bereits kompromittiertes LAN oder ein direkt aus dem Internet erreichbares Admin-Panel voraussetzen, liegen außerhalb des normalen Bedrohungsmodells — Meldungen sind aber trotzdem willkommen.
