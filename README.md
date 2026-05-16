# mcp-lbc

Serveur MCP qui expose les annonces Leboncoin à Claude via la lib [`lbc`](https://github.com/etienne-hd/lbc).

## Prérequis

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Réseau **résidentiel** (les IPs datacenter/VPS sont bloquées par DataDome)

## Installation

```bash
git clone <repo>
cd mcp-leboncoin
uv sync
```

## Outils exposés

| Tool | Description |
|------|-------------|
| `search_ads` | Recherche avec filtres (texte, catégorie, région, prix, pagination) |
| `get_ad_detail` | Détail complet d'une annonce par ID |

> **Rate limit** : `search_ads` est limité à **10 appels/heure** côté serveur pour éviter le blocage DataDome. Au-delà, le tool retourne une erreur avec le temps d'attente restant.

## Intégration Claude Code

```bash
claude mcp add leboncoin -s user -- uv run --project /user/mcp-lbc python /user/mcp-lbc/lbc_mcp_server.py
```

Vérifier avec `/mcp` après avoir redémarré une nouvelle session.

## Intégration Claude Desktop

Ajouter dans `claude_desktop_config.json` :

- **macOS** : `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux** : `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "leboncoin": {
      "command": "uv",
      "args": ["run", "--project", "/chemin/vers/mcp-leboncoin", "python", "/chemin/vers/mcp-leboncoin/lbc_mcp_server.py"]
    }
  }
}
```

## Proxy résidentiel (si IP datacenter)

Dans `lbc_mcp_server.py`, remplacer la ligne `_client = Client(...)` par :

```python
from lbc.model.proxy import Proxy
_client = Client(
    impersonate="safari18_4_ios",
    max_retries=2,
    proxy=Proxy(url="http://user:pass@host:port"),
)
```

## Tests

```bash
uv run python test_mcp_server.py   # teste le serveur MCP via stdio
uv run python test_lbc.py          # teste la lib lbc directement
```
