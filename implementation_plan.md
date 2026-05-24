# Implementierungsplan: mvginfo Skill

## Entscheidungsprotokoll

| Frage | Entscheidung |
|-------|-------------|
| Auslöser | Natürlichsprachliche ÖPNV-Anfragen für München (proaktiv) |
| Ausgabeformat | `--output llm` (TOON-Format) |
| Plattform | `[macos, linux]` |
| Conditional Activation | Keine — immer aktiv |
| Tags | `[Transport, Munich, PublicTransit, Realtime]` |
| Author | `nhranitzky` |

---

## Frontmatter

```yaml
name: mvginfo
description: Real-time Munich public transport — departures, routes, disruptions and station search via MVG CLI
version: 1.0.0
author: nhranitzky
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [Transport, Munich, PublicTransit, Realtime]
```

Keine `required_environment_variables` (MVG-API ist öffentlich).  
Keine `required_credential_files`.  
Keine `config`-Einträge (Pfad über `${HERMES_SKILL_DIR}` abgeleitet).

---

## CLI-Aufruf-Muster

```bash
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm <command> [options]
```

Voraussetzung: `uv` muss im PATH sein. Python ≥ 3.11 wird von `uv` automatisch verwaltet.

---

## SKILL.md Gliederung

### 1. Overview
- Was das CLI macht und wann es nützlich ist
- Hinweis: Nur München / MVG-Netz

### 2. When to Use
**Trigger:**
- Nutzer fragt nach Abfahrtszeiten, Linien, Störungen in München
- Nutzer nennt eine MVG-Station oder Linie (U3, S8, Tram 19 …)
- Nutzer fragt nach der schnellsten Verbindung von A nach B (direkte Verbindung)

**Nicht verwenden für:**
- Verbindungen mit Umstieg → mvg.de aufrufen
- Städte außerhalb des MVG-Netzes
- Fahrplanauskunft mehrere Tage im Voraus

### 3. Commands (je ein Abschnitt)

#### `find-stations`
```bash
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm find-stations --name "Marienplatz"
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm find-stations --lat 48.137 --lng 11.575
```

#### `departures`
```bash
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm departures --station "Marienplatz" --limit 10
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm departures --station "Marienplatz" --transport UBAHN --lines U3,U6
```

#### `route`
```bash
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm route --from "Marienplatz" --to "Hauptbahnhof"
```

#### `disruptions`
```bash
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm disruptions
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm disruptions --lines U3,U6
```
Hinweis: Startet Chromium (Playwright) — erster Aufruf installiert Chromium automatisch.

### 4. Transport Types (Referenztabelle)

| Wert | Verkehrsmittel |
|------|----------------|
| `UBAHN` | U-Bahn |
| `SBAHN` | S-Bahn |
| `TRAM` | Tram |
| `BUS` | Bus |
| `BAHN` | Regionalzug |
| `REGIONAL_BUS` | Regionalbus |

### 5. Common Pitfalls
1. Station nicht gefunden → Globale ID verwenden: `--station de:09162:2`
2. `disruptions` hängt → `python -m playwright install chromium` ausführen
3. `route` findet keine Verbindung → Nur Direktverbindungen; Umstieg über mvg.de
4. `uv` nicht im PATH → Installation: `brew install uv` / `pip install uv`

### 6. Verification Checklist
- [ ] `find-stations` gibt mindestens eine Station zurück
- [ ] `departures` zeigt Echtzeit-Abfahrten mit `in_minutes`
- [ ] `route` zeigt Direktverbindung mit `departs_at`
- [ ] `disruptions` gibt entweder leere Liste oder aktuelle Meldungen zurück

---

## Implementierungs-Checkliste

- [ ] `SKILL.md` Frontmatter schreiben (alle 5 Pflichtfelder + optional)
- [ ] Abschnitt **Overview** schreiben
- [ ] Abschnitt **When to Use** mit Triggern und Gegentriggern schreiben
- [ ] Abschnitt **find-stations** mit Beispielaufruf und Output-Erklärung
- [ ] Abschnitt **departures** mit Beispielaufruf und Filter-Optionen
- [ ] Abschnitt **route** mit Einschränkungshinweis (nur Direktverbindungen)
- [ ] Abschnitt **disruptions** mit Playwright-Hinweis
- [ ] Referenztabelle Transport Types einfügen
- [ ] Abschnitt **Common Pitfalls** (4 Einträge)
- [ ] Abschnitt **Verification Checklist**
- [ ] SKILL.md validieren mit `python3 scripts/validate_skill.py`
- [ ] `README.md` (root) aktualisieren: Beschreibung, Befehle, Konfiguration und Installationshinweise eintragen
