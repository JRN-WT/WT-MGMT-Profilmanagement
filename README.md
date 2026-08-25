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
├── daten/
│   ├── profile/        # lokale Basisprofile als JSON
│   ├── varianten/      # lokale Varianten als JSON
│   ├── dokumente/      # künftige Originale und Exporte
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

Es sind keine externen Python-Pakete erforderlich.

## Testablauf für Varianten

1. Profil öffnen und ein Basisprofil mit mindestens einer Kompetenz speichern.
2. Eine Variante anlegen, Variantenname und Zielrolle ergänzen und als Entwurf speichern.
3. In der Variante Einträge ausblenden, umsortieren, umformulieren oder ergänzen.
4. Im Basisprofil eine Kompetenz oder das Kurzprofil ändern und erneut speichern.
5. Variante öffnen: Status **„Basisprofil aktualisiert“** und Aktion **„Basisänderungen prüfen“** erscheinen.
6. Jeden Unterschied bewusst übernehmen oder die eigene Variantenfassung beibehalten.
7. Prüfung abschließen und Variante freigeben.

## Nächster Ausbau

Der nächste große Baustein ist die Dokumenten- und Exportkette: Originaldokumente zuordnen, Dateien lokal ablegen und aus freigegebenen Varianten kundentaugliche Word-/PDF- und ATS-Fassungen erzeugen.
