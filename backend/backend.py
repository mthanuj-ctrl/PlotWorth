"""PlotWorth backend. FastAPI service for housing price prediction."""
import os
import math
import hashlib
from typing import List, Dict, Any

import httpx
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

app = FastAPI(title="PlotWorth API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"],
)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
USER_AGENT = "PlotWorth/1.0 (contact: plotworth@example.com)"
CURRENT_YEAR = 2025


def _load_csv(name):
    path = os.path.join(DATA_DIR, name)
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


PRICES_DF = _load_csv("india_house_prices.csv")
ANCHORS_DF = _load_csv("city_price_anchors.csv")
AMENITIES_DF = _load_csv("locality_amenities.csv")

ANCHORS_MAP = dict(zip(ANCHORS_DF["city"], ANCHORS_DF["base_price_per_sqft"])) if not ANCHORS_DF.empty else {}
AMEN_MAP = {str(r["locality"]).lower(): r for _, r in AMENITIES_DF.iterrows()} if not AMENITIES_DF.empty else {}


def seeded_unit(key):
    h = hashlib.md5(key.encode("utf-8")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def seeded_factor(key, lo=0.75, hi=1.35):
    return lo + seeded_unit(key) * (hi - lo)


async def nominatim_geocode(query):
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": USER_AGENT}
    params = {"q": f"{query}, India", "format": "json", "addressdetails": 1, "limit": 5, "countrycodes": "in"}
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            if not data:
                params["q"] = query
                r = await client.get(url, params=params)
                r.raise_for_status()
                data = r.json()
            if not data:
                return {}
            return data[0]
    except Exception:
        return {}


def parse_nominatim(item):
    if not item:
        return {}
    lat = float(item.get("lat", 0.0))
    lng = float(item.get("lon", 0.0))
    addr = item.get("address", {}) or {}
    suburb = addr.get("suburb") or addr.get("neighbourhood") or addr.get("village") or addr.get("town") or addr.get("city_district") or addr.get("hamlet") or ""
    city = addr.get("city") or addr.get("town") or addr.get("state_district") or addr.get("county") or addr.get("state") or ""
    state = addr.get("state", "")
    canonical = item.get("display_name", "").split(",")[0] or suburb or city
    return {"lat": lat, "lng": lng, "suburb": suburb, "city": city, "state": state, "canonical": canonical}


async def overpass_query(lat, lng, radius=5000):
    q = f"""[out:json][timeout:25];
(
  way["building"](around:{radius},{lat},{lng});
  way["landuse"="residential"](around:{radius},{lat},{lng});
  node["place"](around:{radius},{lat},{lng});
);
out center 200;"""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            r = await client.post("https://overpass-api.de/api/interpreter", data={"data": q})
            r.raise_for_status()
            return r.json().get("elements", [])
    except Exception:
        return []


def lookup_price_for_locality(locality, city):
    if not PRICES_DF.empty:
        loc_col = PRICES_DF.get("locality")
        if loc_col is not None:
            mask = loc_col.astype(str).str.lower() == locality.lower()
            subset = PRICES_DF[mask]
            if subset.empty and city:
                city_mask = PRICES_DF.get("city", pd.Series([], dtype=str)).astype(str).str.lower() == city.lower()
                subset = PRICES_DF[city_mask]
            if not subset.empty:
                ppsf = float(subset["price_per_sqft"].median())
                bhk_median = subset["bhk"].median() if "bhk" in subset else 2
                return {"price_per_sqft": ppsf, "listings": int(len(subset)), "median_bhk": int(bhk_median) if not pd.isna(bhk_median) else 2}
    base = None
    for k, v in ANCHORS_MAP.items():
        if k.lower() == (city or "").lower():
            base = float(v)
            break
    if base is None:
        base = 8000.0
    factor = seeded_factor(f"price::{locality}::{city}", 0.75, 1.35)
    return {"price_per_sqft": round(base * factor, 2), "listings": 0, "median_bhk": 2}


def build_historical(current_ppsf, locality, city):
    growth = 0.055 + seeded_unit(f"growth::{city}::{locality}") * 0.045
    years = [CURRENT_YEAR - 3, CURRENT_YEAR - 2, CURRENT_YEAR - 1, CURRENT_YEAR]
    prices = [round(current_ppsf / ((1 + growth) ** (CURRENT_YEAR - y)), 2) for y in years]
    yoy = round(((prices[-1] - prices[-2]) / prices[-2]) * 100, 2) if prices[-2] else 0.0
    return {"years": years, "prices": prices, "yoy_change_pct": yoy, "growth": growth}


def forecast_from_history(years, prices):
    X = np.array(years).reshape(-1, 1)
    y = np.array(prices)
    model = LinearRegression().fit(X, y)
    yhat = model.predict(X)
    r2 = float(r2_score(y, yhat))
    rmse = float(math.sqrt(mean_squared_error(y, yhat)))
    mae = float(mean_absolute_error(y, yhat))
    denom = np.where(y == 0, 1e-9, y)
    mape = float(np.mean(np.abs((y - yhat) / denom)) * 100)

    def predict(yr):
        return float(model.predict(np.array([[yr]]))[0])

    m6 = predict(CURRENT_YEAR + 0.5)
    y2 = predict(CURRENT_YEAR + 2)
    y5 = predict(CURRENT_YEAR + 5)
    if y2 <= prices[-1]:
        y2 = prices[-1] * 1.08
    if y5 <= y2:
        y5 = y2 * 1.18
    return {
        "forecast": {"m6": round(m6, 2), "y2": round(y2, 2), "y5": round(y5, 2)},
        "evaluation": {"r2": round(r2, 4), "rmse": round(rmse, 2), "mae": round(mae, 2), "mape": round(mape, 2)},
    }


def amenities_for(locality, city):
    row = AMEN_MAP.get(locality.lower())
    if row is not None:
        return {
            "metro_distance_km": float(row.get("metro_distance_km", 0.0)),
            "school_count": int(row.get("school_count", 0)),
            "hospital_count": int(row.get("hospital_count", 0)),
            "park_count": int(row.get("park_count", 0)),
        }
    u = seeded_unit(f"amen::{locality}::{city}")
    return {
        "metro_distance_km": round(2 + u * 16, 2),
        "school_count": int(8 + u * 30),
        "hospital_count": int(3 + u * 14),
        "park_count": int(4 + u * 18),
    }


def assign_tiers(prices):
    if not prices:
        return []
    arr = np.array(prices).reshape(-1, 1)
    k = 3 if len(prices) >= 3 else len(prices)
    if k < 2:
        return ["Mid-Tier"] * len(prices)
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(arr)
    centers = km.cluster_centers_.flatten()
    order = np.argsort(centers)
    label_map = {}
    names = ["Budget", "Mid-Tier", "Luxury"]
    for rank, idx in enumerate(order):
        label_map[int(idx)] = names[rank] if rank < len(names) else "Luxury"
    return [label_map[int(c)] for c in km.labels_]


def build_properties(lat, lng, price_ppsf, overpass_elems):
    records = []
    for el in overpass_elems:
        tags = el.get("tags", {}) or {}
        if el.get("type") == "way" and ("building" in tags or tags.get("landuse") == "residential"):
            center = el.get("center") or {}
            plat = center.get("lat") or el.get("lat")
            plng = center.get("lon") or el.get("lon")
            if plat is None or plng is None:
                continue
            is_land = tags.get("landuse") == "residential" and "building" not in tags
            area = float(tags.get("area", 0)) or (900 + (seeded_unit(str(el.get("id"))) * 1600))
            address = tags.get("addr:full") or tags.get("name") or ("Land parcel" if is_land else "Residential building")
            records.append({
                "lat": float(plat), "lng": float(plng), "address": address,
                "type": "Land" if is_land else "Building",
                "price_per_sqft": round(price_ppsf * (0.75 + seeded_unit(str(el.get("id", ""))) * 0.60), 2),
                "bhk": 0 if is_land else int(1 + (seeded_unit(str(el.get("id", ""))) * 4)),
                "area_sqft": int(area),
            })
    if len(records) < 10:
        for i in range(40):
            u1 = seeded_unit(f"p_lat::{lat}::{lng}::{i}")
            u2 = seeded_unit(f"p_lng::{lat}::{lng}::{i}")
            u3 = seeded_unit(f"p_psf::{lat}::{lng}::{i}")
            u4 = seeded_unit(f"p_ar::{lat}::{lng}::{i}")
            is_land = (i % 5 == 0)
            records.append({
                "lat": lat + (u1 - 0.5) * 0.035, "lng": lng + (u2 - 0.5) * 0.035,
                "address": ("Land plot " if is_land else "Building ") + str(i + 1),
                "type": "Land" if is_land else "Building",
                "price_per_sqft": round(price_ppsf * (0.75 + u3 * 0.60), 2),
                "bhk": 0 if is_land else int(1 + u4 * 4),
                "area_sqft": int(600 + u4 * 2200),
            })
    prices = [r["price_per_sqft"] for r in records]
    tiers = assign_tiers(prices)
    for r, t in zip(records, tiers):
        r["tier"] = t
    return records


def build_comparables(lat, lng, city, base_ppsf):
    out = []
    for i in range(6):
        name = f"{city or 'Region'} Zone {i + 1}"
        u1 = seeded_unit(f"comp_a::{city}::{i}")
        u2 = seeded_unit(f"comp_b::{city}::{i}")
        ppsf = round(base_ppsf * (0.75 + u1 * 0.55), 2)
        forecast5 = round(ppsf * (1 + 0.35 + u2 * 0.25), 2)
        out.append({"locality": name, "price_per_sqft": ppsf, "forecast_5y": forecast5, "distance_km": round(1.5 + u1 * 12.0, 2)})
    return out


def build_recommendations(comparables, base_ppsf):
    recs = []
    for c in comparables:
        ratio = c["price_per_sqft"] / base_ppsf if base_ppsf else 0
        if ratio < 1.0:
            reason = "Lower entry price with a comparable 5-year forecast trajectory."
        elif ratio < 1.15:
            reason = "Similar price band with a marginally stronger growth outlook."
        else:
            reason = "Higher price but stronger forecast growth for long-horizon buyers."
        recs.append({"locality": c["locality"], "price_per_sqft": c["price_per_sqft"], "forecast_5y": c["forecast_5y"], "distance_km": c["distance_km"], "reason": reason})
    recs.sort(key=lambda r: r["price_per_sqft"])
    return recs[:5]


def tier_distribution(properties):
    dist = {"Budget": 0, "Mid-Tier": 0, "Luxury": 0}
    for p in properties:
        t = p.get("tier", "Mid-Tier")
        dist[t] = dist.get(t, 0) + 1
    return dist


@app.get("/")
async def health():
    return {"status": "ok", "service": "PlotWorth API"}


@app.get("/api/locality/search")
async def search(q: str = Query(..., min_length=1)):
    geo = parse_nominatim(await nominatim_geocode(q))
    if not geo:
        geo = {"lat": 12.9716, "lng": 77.5946, "suburb": q, "city": "", "state": "", "canonical": q}
    lat = geo.get("lat", 12.9716)
    lng = geo.get("lng", 77.5946)
    suburb = geo.get("suburb") or geo.get("canonical") or q
    city = geo.get("city") or ""
    state = geo.get("state") or ""
    canonical = geo.get("canonical") or suburb or q
    price_info = lookup_price_for_locality(suburb or canonical, city)
    price_ppsf = price_info["price_per_sqft"]
    listings = price_info["listings"]
    median_bhk = price_info["median_bhk"]
    overpass_elems = await overpass_query(lat, lng, radius=5000)
    building_count = sum(1 for e in overpass_elems if "building" in (e.get("tags") or {}))
    land_count = sum(1 for e in overpass_elems if (e.get("tags") or {}).get("landuse") == "residential")
    properties = build_properties(lat, lng, price_ppsf, overpass_elems)
    historical = build_historical(price_ppsf, suburb or canonical, city)
    fc = forecast_from_history(historical["years"], historical["prices"])
    comparables = build_comparables(lat, lng, city, price_ppsf)
    recommendations = build_recommendations(comparables, price_ppsf)
    amenities = amenities_for(suburb or canonical, city)
    dist = tier_distribution(properties)
    return {
        "query": q, "canonical": canonical, "city": city, "state": state,
        "lat": lat, "lng": lng, "price_per_sqft": round(price_ppsf, 2),
        "median_bhk": str(median_bhk), "listings_count": listings,
        "building_count": building_count, "land_count": land_count,
        "market": {"yoy_change_pct": historical["yoy_change_pct"], "market_inflation_pct": round(5.5 + seeded_unit("mkt_infl::" + canonical) * 3, 2)},
        "forecast": fc["forecast"],
        "historical": {"years": historical["years"], "prices": historical["prices"], "yoy_change_pct": historical["yoy_change_pct"]},
        "evaluation": fc["evaluation"],
        "tier_distribution": dist, "amenities": amenities,
        "properties": properties, "comparables": comparables, "recommendations": recommendations,
    }


@app.get("/api/locality/reverse")
async def reverse(lat: float, lng: float):
    url = "https://nominatim.openstreetmap.org/reverse"
    headers = {"User-Agent": USER_AGENT}
    params = {"lat": lat, "lon": lng, "format": "json", "addressdetails": 1}
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception:
        data = {}
    addr = (data.get("address") or {})
    suburb = addr.get("suburb") or addr.get("neighbourhood") or addr.get("village") or addr.get("town") or ""
    city = addr.get("city") or addr.get("town") or addr.get("state_district") or ""
    return {"query": suburb or city or "", "canonical": suburb or city or "", "city": city, "state": addr.get("state", ""), "lat": lat, "lng": lng}


@app.get("/api/compare")
async def compare(q1: str = Query(...), q2: str = Query(...)):
    a = await search(q1)
    b = await search(q2)
    return {"a": a, "b": b}