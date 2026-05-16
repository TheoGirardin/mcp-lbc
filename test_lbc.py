#!/usr/bin/env python3
"""
Test de la lib Python `lbc` (github.com/etienne-hd/lbc)
Utilise curl_cffi pour impersoner le TLS iOS/Android et contourner DataDome.

Usage :
    uv run python test_lbc.py

Note sur DataDome :
    La lib contourne DataDome via curl_cffi (TLS fingerprint iOS/Android).
    Cela fonctionne sur réseau résidentiel/mobile.
    Depuis une IP datacenter (cloud, VPS, CI), DataDome bloque en amont
    (HTTP 403 dès le GET initial sur leboncoin.fr), indépendamment du TLS.
    → Exécuter depuis un réseau domestique/mobile pour les endpoints protégés.
"""

import curl_cffi.requests as cffi_requests
from lbc import Client
from lbc.model.enums import Category, Sort, Region, Department
from lbc.exceptions import DatadomeError, NotFoundError, RequestError


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print("=" * 60)


def check_environment() -> bool:
    """Vérifie si l'IP courante passe le filtre DataDome."""
    section("0. Diagnostic environnement")
    for impersonate in ["safari18_4_ios", "chrome136"]:
        session = cffi_requests.Session(impersonate=impersonate)
        session.headers.update({
            "User-Agent": "LBC;iOS;18.4;iPhone;phone;ABCD-1234;wifi;101.45.0"
        })
        r = session.get("https://www.leboncoin.fr/", timeout=10)
        has_dd = bool(r.cookies.get("datadome"))
        status = "✅ passe" if r.status_code == 200 else f"❌ bloqué (HTTP {r.status_code})"
        print(f"  {impersonate:20s}  {status}  cookie datadome: {'oui' if has_dd else 'non'}")
        if r.status_code == 200:
            return True
    return False


def test_location_autocomplete() -> None:
    """
    POST /api/parrot-location/v1/complete/location
    Cet endpoint n'exige pas de session DataDome valide (pas de cookie JS requis).
    Confirmé HTTP 200 le 2025-05-16 depuis curl natif — peut être bloqué si l'IP
    est ultérieurement flaggée après trop de requêtes.
    """
    section("1. Location autocomplete")
    # On utilise curl natif (sans TLS impersonation) — le plus léger
    import subprocess, json as _json
    cmd = [
        "curl", "-s", "-w", "\n%{http_code}",
        "-X", "POST", "https://api.leboncoin.fr/api/parrot-location/v1/complete/location",
        "-H", "User-Agent: LBC;iOS;18.4;iPhone;phone;ABCD-1234;wifi;101.45.0",
        "-H", "api_key: ba0c2dad52b3ec",
        "-H", "Accept: application/json",
        "-H", "Content-Type: application/json",
        "-d", '{"context":[],"text":"Lyon"}',
    ]
    out = subprocess.check_output(cmd, text=True, timeout=15)
    *body_lines, status = out.strip().splitlines()
    body = "\n".join(body_lines)
    print(f"HTTP {status}")
    if status == "200":
        for loc in _json.loads(body)[:4]:
            print(f"  {loc['locationType']:12s} {loc['label']}")
    else:
        print("  ⚠️  IP bloquée (probable flaggage DataDome après tests intensifs)")


def test_search(client: Client) -> list:
    """Recherche vélos en Île-de-France, max 500 €."""
    section("2. Recherche — vélos en Île-de-France, max 500 €")
    results = client.search(
        text="vélo",
        category=Category.LOISIRS_VELOS,
        locations=Region.ILE_DE_FRANCE,
        sort=Sort.NEWEST,
        limit=5,
        price=(0, 500),
    )
    print(f"Total : {results.total} annonces")
    for ad in results.ads:
        price = f"{ad.price:.0f} €" if ad.price else "N/C"
        print(f"  [{ad.id}] {ad.subject[:55]:<55} {price:>8}  {ad.location.city}")
        print(f"    {ad.url}")
    return results.ads


def test_ad_detail(client: Client, ad_id: int) -> None:
    """Détail complet d'une annonce."""
    section(f"3. Détail annonce {ad_id}")
    ad = client.get_ad(ad_id)
    print(f"Titre       : {ad.subject}")
    print(f"Prix        : {ad.price} €")
    print(f"Catégorie   : {ad.category_name} (id={ad.category_id})")
    print(f"Ville       : {ad.location.city} ({ad.location.zipcode})")
    print(f"Téléphone   : {'oui' if ad.has_phone else 'non'}")
    print(f"Images      : {len(ad.images)} photo(s)")
    print(f"Description : {ad.body[:200]}{'…' if len(ad.body) > 200 else ''}")
    print(f"URL         : {ad.url}")


def test_immobilier(client: Client) -> None:
    """Ventes immobilières en Île-de-France."""
    section("5. Immobilier — ventes IDF, 100 k – 500 k €")
    results = client.search(
        category=Category.IMMOBILIER_VENTES_IMMOBILIERES,
        locations=Region.ILE_DE_FRANCE,
        sort=Sort.NEWEST,
        limit=3,
        price=(100_000, 500_000),
    )
    print(f"Total : {results.total} annonces")
    for ad in results.ads:
        price = f"{ad.price:,.0f} €" if ad.price else "N/C"
        print(f"  [{ad.id}] {ad.subject[:55]:<55} {price:>12}  {ad.location.city}")


def test_pagination(client: Client) -> None:
    """Pagination via le paramètre page=2."""
    section("6. Pagination — vélos page 2")
    page2 = client.search(
        text="vélo",
        category=Category.LOISIRS_VELOS,
        locations=Region.ILE_DE_FRANCE,
        sort=Sort.NEWEST,
        limit=3,
        page=2,
        price=(0, 500),
    )
    print(f"{len(page2.ads)} annonces page 2 :")
    for ad in page2.ads:
        price = f"{ad.price:.0f} €" if ad.price else "N/C"
        print(f"  [{ad.id}] {ad.subject[:55]:<55} {price:>8}")


def main() -> None:
    # Toujours tester la localisation (pas de DataDome)
    test_location_autocomplete()

    # Vérifier si l'environnement passe DataDome
    env_ok = check_environment()

    if not env_ok:
        print("\n⚠️  IP datacenter détectée — DataDome bloque en amont du TLS fingerprint.")
        print("   Les endpoints suivants nécessitent un réseau résidentiel ou un proxy résidentiel :")
        print("   • search()    → POST /finder/search")
        print("   • get_ad()    → GET  /api/adfinder/v1/classified/{id}")
        print("   • ad.user     → GET  /api/user-card/v2/{uuid}/infos")
        print("\n   Pour tester depuis ce poste : utiliser un proxy résidentiel :")
        print("   client = Client(proxy=Proxy(url='http://user:pass@host:port'))")
        return

    # Environnement OK — on lance les tests complets
    client = Client(impersonate="safari18_4_ios", max_retries=2)

    ads = test_search(client)

    if ads:
        try:
            test_ad_detail(client, ads[0].id)
        except NotFoundError:
            print("Annonce introuvable.")

    test_immobilier(client)
    test_pagination(client)


if __name__ == "__main__":
    try:
        main()
    except DatadomeError as e:
        print(f"\n❌ DataDome : {e}")
    except Exception as e:
        import traceback
        traceback.print_exc()
