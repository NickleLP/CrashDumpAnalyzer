# CrashDumpAnalyzer

## Voraussetzungen

- Windows-Betriebssystem
- Installierte Windows Debugging Tools (cdb.exe)

### Installation der Windows Debugging Tools

1. Laden Sie das Windows 10 SDK herunter: [Windows 10 SDK Download](https://developer.microsoft.com/de-de/windows/downloads/windows-10-sdk/)
2. Starten Sie das Installationsprogramm.
3. Wählen Sie **"Debugging Tools for Windows"** aus und installieren Sie diese.

**Hinweis:** Notieren Sie sich den Installationspfad von `cdb.exe`. Standardmäßig ist dies `C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe`.

## Anwendung ausführen

1. Laden Sie die neueste Version von `CrashDumpAnalyzer.exe` von den GitHub-Releases herunter.
2. Stellen Sie sicher, dass `cdb.exe` installiert ist.
3. Führen Sie `CrashDumpAnalyzer.exe` aus.
4. Öffnen Sie einen Webbrowser und navigieren Sie zu `http://localhost:5000`.

## Fehlerbehebung

- **Fehler:** `Debugger nicht gefunden`
  - **Lösung:** Stellen Sie sicher, dass `cdb.exe` am erwarteten Ort installiert ist.
