"""Generates a realistic synthetic India housing price dataset for PlotWorth."""
import os
import random
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ANCHORS_PATH = os.path.join(HERE, "data", "city_price_anchors.csv")
OUT_PATH = os.path.join(HERE, "data", "india_house_prices.csv")
SEED = 42
ROWS = 50000

LOCALITY_POOL = {
    "Bangalore": ["Whitefield", "Koramangala", "Indiranagar", "Jayanagar", "HSR Layout", "Electronic City", "Marathahalli", "Bellandur", "Hebbal", "Yelahanka", "Rajajinagar", "Malleshwaram", "BTM Layout", "Sarjapur Road", "Bannerghatta Road"],
    "Mumbai": ["Andheri", "Bandra", "Powai", "Borivali", "Malad", "Thane", "Navi Mumbai", "Chembur", "Dadar", "Worli"],
    "Delhi": ["Dwarka", "Rohini", "Saket", "Vasant Kunj", "Lajpat Nagar", "Karol Bagh", "Pitampura", "Janakpuri"],
    "Hyderabad": ["Gachibowli", "Hitech City", "Banjara Hills", "Jubilee Hills", "Kondapur", "Madhapur", "Kukatpally", "Miyapur"],
    "Chennai": ["Adyar", "Anna Nagar", "T Nagar", "Velachery", "OMR", "Porur", "Tambaram", "Besant Nagar"],
    "Pune": ["Koregaon Park", "Baner", "Hinjewadi", "Wakad", "Kharadi", "Viman Nagar", "Aundh", "Pimpri"],
    "Kolkata": ["Salt Lake", "New Town", "Ballygunge", "Alipore", "Behala", "Howrah"],
    "Ahmedabad": ["Satellite", "Bopal", "Maninagar", "Prahlad Nagar", "Vastrapur"],
    "Jaipur": ["Vaishali Nagar", "Malviya Nagar", "Mansarovar", "C-Scheme"],
    "Vellore": ["Katpadi", "Sathuvachari", "Bagayam", "Thorapadi", "Gandhinagar"],
    "Coimbatore": ["RS Puram", "Peelamedu", "Saibaba Colony", "Gandhipuram"],
    "Kochi": ["Kakkanad", "Edappally", "Fort Kochi", "Marine Drive"],
    "Lucknow": ["Gomti Nagar", "Hazratganj", "Aliganj", "Indira Nagar"],
    "Chandigarh": ["Sector 17", "Sector 22", "Sector 35", "Mohali"],
    "Gurgaon": ["Sector 56", "DLF Phase 3", "Sohna Road", "Golf Course Road"],
    "Noida": ["Sector 62", "Sector 137", "Greater Noida", "Sector 18"],
    "Visakhapatnam": ["MVP Colony", "Gajuwaka", "Madhurawada", "Beach Road"],
    "Nagpur": ["Dharampeth", "Sadar", "Wardha Road", "Manish Nagar"],
    "Indore": ["Vijay Nagar", "Palasia", "Rau", "Bicholi Mardana"],
    "Bhopal": ["Arera Colony", "MP Nagar", "Kolar Road", "Hoshangabad Road"],
}

CITY_GEO = {
    "Bangalore": (12.9716, 77.5946), "Mumbai": (19.0760, 72.8777), "Delhi": (28.6139, 77.2090),
    "Hyderabad": (17.3850, 78.4867), "Chennai": (13.0827, 80.2707), "Pune": (18.5204, 73.8567),
    "Kolkata": (22.5726, 88.3639), "Ahmedabad": (23.0225, 72.5714), "Jaipur": (26.9124, 75.7873),
    "Vellore": (12.9165, 79.1325), "Coimbatore": (11.0168, 76.9558), "Kochi": (9.9312, 76.2673),
    "Lucknow": (26.8467, 80.9462), "Chandigarh": (30.7333, 76.7794), "Gurgaon": (28.4595, 77.0266),
    "Noida": (28.5355, 77.3910), "Visakhapatnam": (17.6868, 83.2185), "Nagpur": (21.1458, 79.0882),
    "Indore": (22.7196, 75.8577), "Bhopal": (23.2599, 77.4126),
}

PROPERTY_TYPES = ["Apartment", "Villa", "Independent House", "Plot"]
TYPE_WEIGHTS = [0.62, 0.13, 0.17, 0.08]
BHK_CHOICES = [1, 2, 3, 4, 5]
BHK_WEIGHTS = [0.12, 0.36, 0.33, 0.14, 0.05]


def main():
    if not os.path.exists(ANCHORS_PATH):
        raise SystemExit("city_price_anchors.csv is missing")
    anchors = pd.read_csv(ANCHORS_PATH).drop_duplicates(subset=["city"]).reset_index(drop=True)
    rng = random.Random(SEED)
    cities = list(LOCALITY_POOL.keys())
    anchor_map = dict(zip(anchors["city"], anchors["base_price_per_sqft"]))
    rows = []
    for i in range(ROWS):
        city = cities[i % len(cities)]
        locality = rng.choice(LOCALITY_POOL[city])
        base = anchor_map.get(city, anchor_map.get("Bangalore", 9500))
        factor = 0.75 + rng.random() * 0.60
        ppsf = base * factor
        ptype = rng.choices(PROPERTY_TYPES, weights=TYPE_WEIGHTS)[0]
        bhk = rng.choices(BHK_CHOICES, weights=BHK_WEIGHTS)[0]
        if ptype == "Plot":
            bhk = 0
            area = rng.choice([1200, 1500, 1800, 2400, 3000, 4000])
            ppsf *= 0.72
        elif ptype == "Villa":
            area = rng.choice([1800, 2200, 2600, 3200, 4000])
        elif ptype == "Independent House":
            area = rng.choice([900, 1200, 1500, 1800, 2200])
        else:
            area = rng.choice([450, 600, 750, 900, 1100, 1300, 1600])
        ppsf = round(ppsf, 2)
        price_inr = int(ppsf * area)
        lat0, lng0 = CITY_GEO.get(city, (12.9716, 77.5946))
        lat = round(lat0 + (rng.random() - 0.5) * 0.28, 6)
        lng = round(lng0 + (rng.random() - 0.5) * 0.28, 6)
        rows.append({
            "city": city, "locality": locality, "bhk": bhk, "area_sqft": area,
            "price_per_sqft": ppsf, "price_inr": price_inr, "latitude": lat, "longitude": lng,
            "property_type": ptype, "year_built": rng.randint(1995, 2024),
        })
    df = pd.DataFrame(rows)
    df.to_csv(OUT_PATH, index=False)
    print("Wrote", OUT_PATH, "rows:", len(df))


if __name__ == "__main__":
    main()