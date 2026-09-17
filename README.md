# mcp-lbc

Serveur MCP qui expose les annonces Leboncoin à Claude via la lib [`lbc`](https://github.com/etienne-hd/lbc).

## Prompt

En utilisant le serveur mcp leboncoin, les indications dans @pc-fixe/pc-fixe.md, fais des recherches leboncoin afin de trouver les meilleurs affaires 
En plus des informations que tu as déjà, j'aimerai que le PC ait une carte graphique haut de gamme (type RX 7900 XTX, RX 9070 XT, RX 6900 XT, ...), même si le reste du PC est beaucoup plus bas de gamme (upgradedable)

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

> **Rate limit** : `search_ads` est limité à **10 appels/heure** côté serveur pour éviter le blocage DataDome. Au-delà, le tool retourne une erreur avec le temps d'attente restant. Voir [`AGENTS.md`](./AGENTS.md) pour les règles d'usage côté agent.

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

## Tests

```bash
uv run python test_mcp_server.py   # teste le serveur MCP via stdio
uv run python test_lbc.py          # teste la lib lbc directement
```
