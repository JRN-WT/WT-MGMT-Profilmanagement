# WERK TRIFFT – Profilmanagement

Eigenständiger, lokal betreibbarer Kern für interne Beraterprofile und kundenspezifische Profilvarianten.

## Arbeitsprinzip

- Das **Basisprofil** ist die vollständige interne Quelle.
- Eine **Variante** ist eine eigenständig bearbeitbare Kundenfassung. Sie kann Inhalte anders formulieren, ergänzen, ausblenden und priorisieren, ohne das Basisprofil zu verändern.
- Jede fachliche Änderung am Basisprofil erhöht dessen Revision und markiert bestehende Varianten mit **„Basisprofil aktualisiert“**.
- In der Variante werden Änderungen über **„Basisänderungen prüfen“** bewusst übernommen oder als eigene Kundenfassung beibehalten. Erst danach kann die Variante wieder freigegeben werden.

## Lokale Struktur

```text
profilmanagement/
├── profilmanagement.html
├── profilmanagement-server.py
├── profilmanagement_pdf_playwright.py
├── daten/
│   ├── profile/        # lokale Basisprofile als JSON
│   ├── varianten/      # lokale Varianten als JSON
│   ├── dokumente/      # lokal erzeugte PDF-Dateien
│   └── archiv/         # archivierte Profilakten
└── README.md
```

`daten/` enthält personenbezogene Profilakten und bleibt lokal beziehungsweise im Nextcloud-synchronisierten Projektordner. Es wird nicht nach GitHub versioniert.

## Starten

Im Projektordner ausführen:

```bash
python profilmanagement-server.py
```

Danach im Browser öffnen:

```text
http://127.0.0.1:8081/profilmanagement.html
```

## PDF-Export einrichten

Der PDF-Export nutzt Playwright und Chromium. Die Profilpflege selbst benötigt diese Zusatzbibliothek nicht und bleibt ohne sie vollständig nutzbar.

Einmalig im Projektordner ausführen:

```bash
pip install playwright
playwright install chromium
```

Optional kann ein farbiges `logo_werktrifft.png` im Projektverzeichnis, im Unterordner `assets/` oder im benachbarten Ordner `WT-Dashboard-Module/` abgelegt werden. Beim Export wird es direkt in das PDF eingebettet. Ohne Logo verwendet das Dokument einen typografischen WERK-TRIFFT-Schriftzug.

## PDF einer Variante erzeugen

1. Profil und gewünschte Variante öffnen.
2. Inhalte ein- oder ausblenden und in die gewünschte Reihenfolge bringen.
3. In der rechten Vorschau **„PDF aus dieser Vorschau erstellen“** auswählen.
4. Die PDF wird heruntergeladen und zusätzlich unter `daten/dokumente/<profil-id>/` abgelegt.

Der Export verwendet genau den sichtbaren Stand der Vorschau – auch wenn Kontext, Auswahl oder Reihenfolge noch nicht gespeichert wurden. Er verändert weder die gespeicherte Variante noch ihren Freigabestatus.

## Testablauf für Varianten

1. Profil öffnen und ein Basisprofil mit mindestens einer Kompetenz speichern.
2. Eine Variante anlegen, Variantenname und Zielrolle ergänzen und als Entwurf speichern.
3. In der Variante Einträge ausblenden und umsortieren.
4. Vorschau öffnen und prüfen, dass ausschließlich aktivierte Einträge in der gewählten Reihenfolge erscheinen.
5. **„PDF aus dieser Vorschau erstellen“** auswählen und den Download prüfen.
6. Prüfen, dass die PDF unter `daten/dokumente/<profil-id>/` liegt und die Variante unverändert bleibt.
7. Im Basisprofil eine Kompetenz oder das Kurzprofil ändern und erneut speichern.
8. Variante öffnen: Status **„Basisprofil aktualisiert“** und Aktion **„Basisänderungen prüfen“** erscheinen.

## Nächster Ausbau

Der nächste große Baustein ist die Dokumentenkette: Originaldokumente zuordnen, Dateien lokal ablegen und aus freigegebenen Varianten kundentaugliche Word- und ATS-Fassungen erzeugen.
