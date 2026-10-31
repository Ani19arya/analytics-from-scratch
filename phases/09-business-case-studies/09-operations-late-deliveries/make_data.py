"""Build data/shipments.csv for the Parcelwren late deliveries case.

The data is synthetic and deterministic (fixed seed). Parcelwren is a
fictional online retailer of home and garden goods that ships from two
warehouses, North and South, with two carriers, A and B. One row per shipment
for orders placed from Monday 6 July to Sunday 27 September 2026 (12 weeks).

Columns: shipment_id, order_ts, warehouse, carrier, zone (delivery zone 1 to
3, further away is higher), packed_ts, collected_ts (when the carrier picked
the parcel up from the warehouse), delivered_ts, promised_date (the customer
was promised delivery by the end of this day: order date + 2 days).
Timestamps are local time, 'YYYY-MM-DD HH:MM'.

How a shipment moves: the warehouse packs it a few hours after the order;
it waits for the carrier's daily collection; the carrier delivers it.

The story planted in the data: until week 6 both warehouses have a daily
carrier collection at 18:00. From week 7 (Monday 17 August) the carrier
collects from South at 15:00 instead. Parcels packed at South between 15:00
and 18:00 now wait almost a day longer. Nothing else changes: carrier B is a
little slower than A all along, and pack times stay the same.

    python3 make_data.py                         writes data/shipments.csv (seed 909)
    import make_data; make_data.build(seed=4)    returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 909
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "shipments.csv")
START = datetime.date(2026, 7, 6)
DAYS = 84
CHANGE_WEEK = 7
FIELDS = ["shipment_id", "order_ts", "warehouse", "carrier", "zone", "packed_ts", "collected_ts",
          "delivered_ts", "promised_date"]
FMT = "%Y-%m-%d %H:%M"
OLD_HOUR, NEW_HOUR = 20, 16
PACK_MIN, PACK_MAX = 30, 180
T0, TZ, TB, TSD = 24, 3, 3, 4
FAILED_ATTEMPT = 0.03  # first delivery attempt fails, parcel comes back the next day


def next_collection(packed, hour):
    """The first daily collection at `hour`:00 at or after the packed time."""
    c = datetime.datetime.combine(packed.date(), datetime.time(hour, 0))
    return c if packed <= c else c + datetime.timedelta(days=1)


def build(seed=SEED):
    """Return {"shipments": [row, ...]}, each row a dict of text values as written to the CSV."""
    rng = random.Random(seed)
    rows = []
    n = 0
    for offset in range(DAYS):
        day = START + datetime.timedelta(days=offset)
        week = offset // 7 + 1
        for _ in range(int(round(rng.gauss(21, 3)))):
            n += 1
            minute = int(rng.triangular(7 * 60, 20 * 60, 12 * 60))
            order = datetime.datetime.combine(day, datetime.time(0, 0)) + datetime.timedelta(minutes=minute)
            warehouse = "North" if rng.random() < 0.55 else "South"
            carrier = "A" if rng.random() < 0.6 else "B"
            zone = rng.choice((1, 1, 2, 2, 3))
            packed = order + datetime.timedelta(minutes=int(rng.uniform(PACK_MIN, PACK_MAX)))
            hour = NEW_HOUR if (warehouse == "South" and week >= CHANGE_WEEK) else OLD_HOUR
            collected = next_collection(packed, hour) + datetime.timedelta(minutes=int(rng.uniform(0, 40)))
            transit_h = rng.gauss(T0 + TZ * zone + (TB if carrier == "B" else 0), TSD)
            delivered = collected + datetime.timedelta(minutes=int(max(10.0, transit_h) * 60))
            # deliveries happen 08:00 to 21:00: anything outside moves to 08:00 the next morning
            if delivered.hour >= 21:
                delivered = datetime.datetime.combine(delivered.date() + datetime.timedelta(days=1),
                                                      datetime.time(8, 0)) + datetime.timedelta(minutes=rng.randint(0, 90))
            elif delivered.hour < 8:
                delivered = datetime.datetime.combine(delivered.date(), datetime.time(8, 0)) + \
                    datetime.timedelta(minutes=rng.randint(0, 90))
            if rng.random() < FAILED_ATTEMPT:
                delivered += datetime.timedelta(days=1)
            rows.append({
                "shipment_id": "P%05d" % n,
                "order_ts": order.strftime(FMT),
                "warehouse": warehouse,
                "carrier": carrier,
                "zone": str(zone),
                "packed_ts": packed.strftime(FMT),
                "collected_ts": collected.strftime(FMT),
                "delivered_ts": delivered.strftime(FMT),
                "promised_date": (day + datetime.timedelta(days=2)).isoformat(),
            })
    return {"shipments": rows}


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["shipments"]
    write_csv(rows, OUT)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
