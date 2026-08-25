# WERK TRIFFT – Profilmanagement

Lokaler Kern für die Verwaltung von Beraterprofilen und kundenbezogenen Profilvarianten.

## Eine klare Ablage, keine Doppelung

Der Projektordner wird in einem **Nextcloud-synchronisierten Bereich** lokal geklont.

- **GitHub** enthält ausschließlich Programmcode und technische Dokumentation.
- **Nextcloud** synchronisiert den gesamten lokalen Projektordner.
- `daten/` ist der **einzige** lokale Speicherort für produktive Profilakten.
- `.gitignore` verhindert, dass JSON-Profilakten und Originaldokumente nach GitHub gelangen.

```text
WT-MGMT-Profilmanagement/
├── profilmanagement.html
├── profilmanagement-server.py
├── README.md
├── .gitignore
└── daten/
    ├── profile/                   # JSON-Basisprofile
    ├── varianten/<profil-id>/     # JSON-Profilvarianten
    ├── dokumente/<profil-id>/     # Originale, Eingänge und Exporte
    └── archiv/                    # archivierte Profilakten
```

## Lokale Einrichtung

1. Repository mit GitHub Desktop in den vorgesehenen Nextcloud-Projektordner klonen.
2. Den Branch `feature/json-profilpersistenz-clean` auswählen.
3. Server im Repository-Ordner starten:

   **macOS**
   ```bash
   python3 profilmanagement-server.py
   ```

   **Windows**
   ```powershell
   py profilmanagement-server.py
   ```

4. Browser öffnen:
   ```text
   http://127.0.0.1:8081/profilmanagement.html
   ```

Der Server erstellt die Unterordner unter `daten/` beim ersten Start automatisch.

## Datenschutz

Die echten Profilakten liegen ausschließlich lokal in `daten/` und werden über Nextcloud synchronisiert. Sie sind ausdrücklich kein Bestandteil des GitHub-Repositories.
