import json

path = "players_labeled.json"

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

counts = {
    "bufon_confirmed": 0,
    "bufon_not_confirmed": 0,
    "leyenda_confirmed": 0,
    "leyenda_not_confirmed": 0,
    "camiseta_confirmed": 0,
    "camiseta_not_confirmed": 0,
}

for p in data:
    # case-insensitive lookup for keys like "status" / "Status"
    def _get_ci(d, key):
        # return first value where key matches case-insensitively
        if key in d:
            return d[key]
        low = key.lower()
        for k, v in d.items():
            if isinstance(k, str) and k.lower() == low:
                return v
        return None

    status = _get_ci(p, "status")
    confirmed = _get_ci(p, "confirmed")

    # normalize types
    if isinstance(status, str):
        status = status.lower()

    if isinstance(confirmed, str):
        c = confirmed.strip().lower()
        if c in ("true", "1", "yes"):  # tolerant parsing
            confirmed = True
        elif c in ("false", "0", "no"):
            confirmed = False
    # now count
    if status in ("bufon", "leyenda", "camiseta"):
        if confirmed is True:
            counts[f"{status}_confirmed"] += 1
        else:
            counts[f"{status}_not_confirmed"] += 1

for k, v in counts.items():
    print(f"{k}: {v}")
