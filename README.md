# WERK TRIFFT – Profilmanagement

Eigenständiger, lokal betreibbarer Kern für die Verwaltung von Beraterprofilen und kundenspezifischen Profilvarianten.

## Ziel des ersten produktiven Schritts

- Profilakten als JSON-Dateien verwalten
- Varianten getrennt von Basisprofilen speichern
- Originaldokumente in der Profilakte ablegen
- Änderungen und Status nachvollziehbar protokollieren
- Löschen durch Archivieren ersetzen
- Auf macOS und Windows ohne externe Python-Pakete lauffähig bleiben
- Serverlogik später einfach in das bestehende WERK-TRIFFT-Managementsystem integrieren

## Geplante Struktur

```text
profilmanagement/
├── profilmanagement.html
├── profilmanagement-server.py
├── daten/
│   ├── profile/
│   ├── varianten/
│   ├── dokumente/
│   └── archiv/
└── README.md
```

## Entwicklung

Die produktive Umsetzung erfolgt zunächst im Branch `feature/json-profilpersistenz`.
