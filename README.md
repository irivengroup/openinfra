# OpenInfra v0.29.79

## v0.29.79 — Profils protocoles Discovery SNMP/SSH/WinRM sécurisés

OpenInfra v0.29.79 poursuit P14 / EPIC-1403 en ajoutant un référentiel de profils protocoles Discovery pour SNMP, SSH et WinRM. Les profils centralisent scope, port, timeout, concurrence maximale, rate limit, retry et référence `vault://` sans jamais matérialiser de secret dans les sorties publiques. Les plans discovery locaux Lite/Pro peuvent désormais s'appuyer sur un profil et héritent alors de ses bornes opérationnelles, tout en restant plan-only, sans scan réseau exécuté et sans mutation RSOT.
