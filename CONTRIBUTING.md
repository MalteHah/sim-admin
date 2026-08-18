# Mitwirken

1. Änderungen in einem eigenen Branch entwickeln.
2. Keine realen SIM-, Benutzer- oder Zugangsdaten als Testwerte verwenden.
3. Vor einem Commit `python -m pytest -q` ausführen.
4. Hardware-Schreibpfade zusätzlich mit Adaptertests absichern.
5. Änderungen an Verhalten, Datenmodell oder Sicherheit im `CHANGELOG.md` und
   gegebenenfalls in `docs/project-history.md` dokumentieren.

Pull Requests sollten Zweck, Sicherheitsauswirkung und durchgeführte Tests kurz
beschreiben. Tests auf echter Hardware dürfen nur mit dafür vorgesehenen
Testkarten erfolgen.
