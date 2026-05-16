#!/usr/bin/env python3
"""
MCP server for Leboncoin — wraps the `lbc` Python library.

Exposed tools:
  - search_ads    : search listings with filters
  - get_ad_detail : full detail of one listing by ID

Run:
    uv run python lbc_mcp_server.py
"""

from __future__ import annotations

import json
import time
from collections import deque
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from lbc import Client
from lbc.model.enums import Category, Sort, Region, Department
from lbc.exceptions import DatadomeError, NotFoundError

mcp = FastMCP("leboncoin")

_client: Client | None = None

# DataDome flags the session after ~10 searches par fenêtre glissante d'1 heure.
_SEARCH_LIMIT = 10
_SEARCH_WINDOW = 3600  # secondes
_search_timestamps: deque[float] = deque()


def _check_rate_limit() -> str | None:
    """Retourne un message d'erreur JSON si la limite est atteinte, sinon None."""
    now = time.monotonic()
    while _search_timestamps and now - _search_timestamps[0] > _SEARCH_WINDOW:
        _search_timestamps.popleft()
    if len(_search_timestamps) >= _SEARCH_LIMIT:
        oldest = _search_timestamps[0]
        wait = int(_SEARCH_WINDOW - (now - oldest)) + 1
        return json.dumps({
            "error": f"Rate limit atteint ({_SEARCH_LIMIT} recherches/heure). "
                     f"Réessayez dans {wait // 60} min {wait % 60} s."
        })
    _search_timestamps.append(now)
    return None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(impersonate="safari18_4_ios", max_retries=2)
    return _client


def _ad_to_dict(ad) -> dict:
    return {
        "id": ad.id,
        "subject": ad.subject,
        "price": ad.price,
        "url": ad.url,
        "city": ad.location.city,
        "zipcode": ad.location.zipcode,
        "department": ad.location.department_name,
        "region": ad.location.region_name,
        "category": ad.category_name,
        "first_publication_date": str(ad.first_publication_date) if ad.first_publication_date else None,
        "has_phone": ad.has_phone,
        "images_count": len(ad.images) if ad.images else 0,
    }


@mcp.tool()
def search_ads(
    text: Annotated[str, "Mots-clés de recherche (ex: 'vélo', 'iPhone 14')"] = "",
    category: Annotated[
        str,
        "Catégorie (ex: 'LOISIRS_VELOS', 'VEHICULES_VOITURES', 'IMMOBILIER_VENTES_IMMOBILIERES'). "
        "Valeur vide = toutes catégories.",
    ] = "",
    region: Annotated[
        str,
        "Région (ex: 'ILE_DE_FRANCE', 'AUVERGNE_RHONE_ALPES', 'BRETAGNE'). Vide = France entière.",
    ] = "",
    sort: Annotated[
        Literal["NEWEST", "OLDEST", "CHEAPEST", "EXPENSIVE", "RELEVANCE"],
        "Tri des résultats.",
    ] = "NEWEST",
    limit: Annotated[int, "Nombre max d'annonces à retourner (1-35)."] = 10,
    page: Annotated[int, "Numéro de page (commence à 1)."] = 1,
    price_min: Annotated[int, "Prix minimum en euros (0 = pas de minimum)."] = 0,
    price_max: Annotated[int, "Prix maximum en euros (0 = pas de maximum)."] = 0,
) -> str:
    """Recherche des annonces Leboncoin avec filtres. Limité à 10 requêtes/heure (DataDome)."""
    if err := _check_rate_limit():
        return err
    client = _get_client()

    kwargs: dict = {
        "sort": Sort[sort],
        "limit": min(max(limit, 1), 35),
        "page": page,
    }

    if text:
        kwargs["text"] = text

    if category:
        try:
            kwargs["category"] = Category[category]
        except KeyError:
            valid = [e.name for e in Category][:20]
            return json.dumps({"error": f"Catégorie '{category}' inconnue. Exemples: {valid}"})

    if region:
        try:
            kwargs["locations"] = Region[region]
        except KeyError:
            valid = [e.name for e in Region][:10]
            return json.dumps({"error": f"Région '{region}' inconnue. Exemples: {valid}"})

    if price_min > 0 or price_max > 0:
        pmin = price_min if price_min > 0 else 0
        pmax = price_max if price_max > 0 else 0
        if pmax > 0:
            kwargs["price"] = (pmin, pmax)
        else:
            kwargs["price"] = (pmin, 9_999_999)

    try:
        results = client.search(**kwargs)
    except DatadomeError as e:
        return json.dumps({"error": f"DataDome: {e}. Utilisez un réseau résidentiel."})

    ads = [_ad_to_dict(ad) for ad in results.ads]
    return json.dumps({
        "total": results.total,
        "max_pages": results.max_pages,
        "page": page,
        "count": len(ads),
        "ads": ads,
    }, ensure_ascii=False)


@mcp.tool()
def get_ad_detail(
    ad_id: Annotated[int, "Identifiant numérique de l'annonce Leboncoin."],
) -> str:
    """Retourne le détail complet d'une annonce Leboncoin (description, prix, localisation, images)."""
    client = _get_client()
    try:
        ad = client.get_ad(ad_id)
    except NotFoundError:
        return json.dumps({"error": f"Annonce {ad_id} introuvable."})
    except DatadomeError as e:
        return json.dumps({"error": f"DataDome: {e}. Utilisez un réseau résidentiel."})

    attributes = {}
    if ad.attributes:
        for attr in ad.attributes:
            attributes[attr.key] = attr.value

    return json.dumps({
        "id": ad.id,
        "subject": ad.subject,
        "body": ad.body,
        "price": ad.price,
        "url": ad.url,
        "category": ad.category_name,
        "category_id": ad.category_id,
        "location": {
            "city": ad.location.city,
            "zipcode": ad.location.zipcode,
            "department": ad.location.department_name,
            "region": ad.location.region_name,
            "lat": ad.location.lat,
            "lng": ad.location.lng,
        },
        "has_phone": ad.has_phone,
        "images": ad.images if ad.images else [],
        "images_count": len(ad.images) if ad.images else 0,
        "attributes": attributes,
        "first_publication_date": str(ad.first_publication_date) if ad.first_publication_date else None,
        "expiration_date": str(ad.expiration_date) if ad.expiration_date else None,
    }, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
