# AGENTS.md

Règles de travail pour les agents IA intervenant dans ce repo.

## Règle 1 — Limite d'appels API Leboncoin (DataDome)

Le tool MCP `leboncoin.search_ads` est **limité à 10 appels par fenêtre glissante de 60 min** côté serveur (cf. `lbc_mcp_server.py:_check_rate_limit`). Au-delà, l'API retourne une erreur avec le temps d'attente restant.

**Caractéristiques confirmées par test (03/07/2026)** :
- **LIMIT = 10**, **WINDOW = 3600 s** (1h)
- **Deque global partagé** : toutes les sessions/agents qui utilisent le même serveur MCP partagent le quota
- **Taux max durable** : 1 req / 6 min (= 60/10, étalé uniformément)
- **Taux post-burst** : ~1 req / 6-10 min (selon la concentration des timestamps)
- **Erreur retourne le temps exact avant reset** : `"Réessayez dans X min Y s"` basé sur le timestamp le plus ancien

**Conséquence** :
- **Toujours** pré-calculer la valeur des recherches avant d'appeler `search_ads` (regarder l'Excel d'historique, lire le `*.md` de contexte, identifier les IDs déjà connus à exclure).
- **Toujours** paralléliser `search_ads` + `get_ad_detail` dans une même vague d'outils pour optimiser le quota.
- **Toujours** remonter le décompte restant à l'utilisateur quand on approche de 9/10.
- **Ne jamais** spammer de requêtes exploratoires : chaque `search_ads` doit viser un signal précis (GPU cible, fourchette de prix, tri).
- **Tenir compte du quota partagé** : si d'autres agents tournent en parallèle, le quota effectif est < 10/60min.

## Règle 2 — Python : utiliser `uv`

Toutes les commandes Python dans ce repo **doivent** passer par `uv` :

```bash
# Run direct
uv run python script.py

# Avec dépendance one-shot
uv run --with openpyxl python3 -c "..."

# Install des deps du projet
uv sync
```

**Interdit** : `python`, `python3`, `pip install`, `pip3 install` directs. Le projet gère ses dépendances via `pyproject.toml` + `uv.lock`.

## Règle 3 — Domaines spécifiques

Les règles de domaine (critères d'achat PC, critères voiture, etc.) vivent dans les fichiers de contexte de chaque sous-dossier :

- `@pc-fixe/pc-fixe.md` — critères PC gaming fixe
- `@voiture/voiture-recherche.md` — critères recherche voiture
- `@<dossier>/<topic>.md` — pour tout autre domaine

Toujours lire le `.md` du dossier concerné **avant** toute recherche LBC.

## Règle 4 — Quota API atteint

Si on atteint la limite 10/10 en cours de session :
1. **Stopper** immédiatement les appels LBC.
2. Lister à l'utilisateur les deals déjà collectés (déjà intégrés à l'Excel).
3. Indiquer la fenêtre temporelle avant reset (l'erreur du serveur donne l'info précise : `"Réessayez dans X min Y s"`).
4. Si le quota est partagé (autres agents), estimer un délai plus long.
5. Ne pas tenter de contourner (pas de re-login, pas de proxy sauvage).

## Règle 5 — Stratégie durable de recherche

Pour maximiser le nombre de recherches utiles :
- **Étaler les reqs** : viser 1 req / 6 min en steady-state pour ne jamais saturer
- **Batch les détails** : 1 `search_ads` + N `get_ad_detail` en parallèle (les `get_ad_detail` ne consomment pas le quota)
- **Réutiliser les résultats** : mettre à jour l'Excel avec les IDs trouvés pour ne pas re-chercher les mêmes annonces
- **Pré-filtrer dans le prompt** : lire le `*.md` de domaine avant de chercher pour cibler les modèles/prix/régions
