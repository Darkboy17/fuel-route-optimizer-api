"""
Utility to check for duplicate coordinates and messy keys in the city cache.
This script reads the city cache JSON file, identifies duplicate coordinates (same lat/lon for different cities) and messy keys (same city/state but different formatting), and prints the findings.
Usage:
    python check_duplicates_in_cache.py
    Make sure to adjust the file path if your cache is located elsewhere.
"""


import json
from collections import defaultdict


def check_duplicates_in_cache(file_path="data/city_cache.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        cache = json.load(f)

    coord_map = defaultdict(list)
    normalized_key_map = defaultdict(list)

    def normalize_key(key):
        city, state = key.split(",")
        return f"{city.strip().upper()},{state.strip().upper()}"

    for key, coords in cache.items():
        # Track duplicate coordinates
        coord_tuple = tuple(coords)
        coord_map[coord_tuple].append(key)

        # Track messy/duplicate keys after normalization
        normalized = normalize_key(key)
        normalized_key_map[normalized].append(key)

    print("\n🔍 Duplicate Coordinates:")
    found = False
    for coords, keys in coord_map.items():
        if len(keys) > 1:
            found = True
            print(f"\nCoords {coords} used by:")
            for k in keys:
                print("  ", k)

    if not found:
        print("No duplicate coordinates found.")

    print("\n🔍 Duplicate Keys After Normalization:")
    found = False
    for norm_key, keys in normalized_key_map.items():
        if len(keys) > 1:
            found = True
            print(f"\nNormalized: {norm_key}")
            for k in keys:
                print("  ", k)

    if not found:
        print("No duplicate normalized keys found.")

if __name__ == "__main__":
    check_duplicates_in_cache()