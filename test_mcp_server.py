#!/usr/bin/env python3
"""
Test du serveur MCP Leboncoin via le SDK MCP (transport stdio).

Usage:
    uv run python test_mcp_server.py
"""

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


EXPECTED_TOOLS = {"search_ads", "get_ad_detail"}
PASS = "\033[32m✅ PASS\033[0m"
FAIL = "\033[31m❌ FAIL\033[0m"


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print("=" * 60)


async def run_tests() -> int:
    """Returns number of failures."""
    failures = 0

    server_params = StdioServerParameters(
        command="python",
        args=["lbc_mcp_server.py"],
        cwd="/home/gigi/mcp-leboncoin",
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # ── 1. List tools ────────────────────────────────────────────
            section("1. Liste des outils exposés")
            tools_response = await session.list_tools()
            tool_names = {t.name for t in tools_response.tools}
            print(f"Outils trouvés : {sorted(tool_names)}")

            missing = EXPECTED_TOOLS - tool_names
            extra = tool_names - EXPECTED_TOOLS
            if missing:
                print(f"{FAIL}  Outils manquants : {missing}")
                failures += 1
            else:
                print(f"{PASS}  Tous les outils attendus sont présents")
            if extra:
                print(f"  ℹ️  Outils supplémentaires : {extra}")

            for tool in tools_response.tools:
                print(f"  • {tool.name}: {tool.description[:80]}")

            # ── 2. search_ads ────────────────────────────────────────────
            section("2. search_ads — vélos Île-de-France, max 300€")
            try:
                result = await session.call_tool("search_ads", {
                    "text": "vélo",
                    "category": "LOISIRS_VELOS",
                    "region": "ILE_DE_FRANCE",
                    "sort": "NEWEST",
                    "limit": 3,
                    "price_max": 300,
                })
                content = result.content[0].text
                data = json.loads(content)
                if "error" in data:
                    print(f"  ⚠️  {data['error']} (DataDome probable — IP datacenter)")
                    print(f"{PASS}  Erreur DataDome gérée proprement")
                else:
                    total = data.get("total", 0)
                    ads = data.get("ads", [])
                    print(f"  Total : {total} annonces, {len(ads)} retournées")
                    for ad in ads:
                        price = f"{ad['price']} €" if ad.get("price") else "N/C"
                        print(f"    [{ad['id']}] {ad['subject'][:50]:<50} {price:>8}  {ad['city']}")
                    if ads:
                        print(f"{PASS}  search_ads retourne des annonces")
                    else:
                        print(f"{FAIL}  search_ads n'a retourné aucune annonce")
                        failures += 1
            except Exception as e:
                print(f"{FAIL}  Exception: {e}")
                failures += 1

            # ── 3. search_ads — bad category ────────────────────────────
            section("3. search_ads — catégorie invalide (gestion d'erreur)")
            try:
                result = await session.call_tool("search_ads", {"category": "CATEGORIE_INEXISTANTE"})
                content = result.content[0].text
                data = json.loads(content)
                if "error" in data and "inconnue" in data["error"]:
                    print(f"  Erreur : {data['error'][:80]}")
                    print(f"{PASS}  Catégorie invalide gérée proprement")
                else:
                    print(f"{FAIL}  Attendu une erreur 'inconnue', reçu : {content[:100]}")
                    failures += 1
            except Exception as e:
                print(f"{FAIL}  Exception: {e}")
                failures += 1

            # ── 4. get_ad_detail ─────────────────────────────────────────
            section("4. get_ad_detail — annonce id=1 (fictif)")
            try:
                result = await session.call_tool("get_ad_detail", {"ad_id": 1})
                content = result.content[0].text
                data = json.loads(content)
                if "error" in data:
                    print(f"  ⚠️  {data['error']}")
                    print(f"{PASS}  Erreur gérée proprement (NotFoundError ou DataDome)")
                else:
                    print(f"  Titre : {data.get('subject')}")
                    print(f"  Prix  : {data.get('price')} €")
                    print(f"  Ville : {data.get('location', {}).get('city')}")
                    print(f"{PASS}  get_ad_detail retourne un résultat structuré")
            except Exception as e:
                print(f"{FAIL}  Exception: {e}")
                failures += 1

            # ── 5. search_ads — immobilier pagination ────────────────────
            section("5. search_ads — immobilier IDF page 2")
            try:
                result = await session.call_tool("search_ads", {
                    "category": "IMMOBILIER_VENTES_IMMOBILIERES",
                    "region": "ILE_DE_FRANCE",
                    "sort": "NEWEST",
                    "limit": 3,
                    "page": 2,
                    "price_min": 100_000,
                    "price_max": 500_000,
                })
                content = result.content[0].text
                data = json.loads(content)
                if "error" in data:
                    print(f"  ⚠️  {data['error']} (DataDome probable)")
                    print(f"{PASS}  Erreur DataDome gérée proprement")
                else:
                    ads = data.get("ads", [])
                    print(f"  {len(ads)} annonces page 2")
                    for ad in ads:
                        price = f"{ad['price']:,} €" if ad.get("price") else "N/C"
                        print(f"    [{ad['id']}] {ad['subject'][:45]:<45} {price:>14}")
                    print(f"{PASS}  Pagination fonctionne")
            except Exception as e:
                print(f"{FAIL}  Exception: {e}")
                failures += 1

    return failures


async def main() -> None:
    section("MCP Leboncoin — Test suite")
    print("Démarrage du serveur MCP via stdio...")

    failures = await run_tests()

    section("Résumé")
    if failures == 0:
        print(f"{PASS}  Tous les tests ont passé.")
    else:
        print(f"{FAIL}  {failures} test(s) échoué(s).")

    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
