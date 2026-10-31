"""Build data/applications.csv: a SYNTHETIC log of 60 job applications by one fictional job seeker,
pulled on 31 October 2026.

Every company, date, channel mix and rate below is invented by this script to teach the
method. The reply, interview and offer chances per channel are made up, not market rates,
and the company names are fictional (several are reused from other lessons in this course).

Columns: app_id, company, channel (referral, careers_page, job_board, recruiter), applied_on,
reply_on (first human reply, a screen invite or a rejection), interview_on (first interview
held), offer_on, rejected_on (date of a rejection at any stage), hours_spent. A blank date
means it has not happened by the pull date. Career-page applications are weighted towards
the last three weeks, so many of them are still waiting: that is the censoring trap.

Run: python3 make_data.py
"""
import csv
import datetime
import os
import random

DEFAULT_SEED = 1106
AS_OF = datetime.date(2026, 10, 31)
FIRST_DAY = datetime.date(2026, 8, 24)

CHANNEL_COUNTS = {"job_board": 26, "careers_page": 18, "recruiter": 9, "referral": 7}
# Made-up chances, for teaching only.
P_REPLY = {"referral": 0.85, "recruiter": 0.65, "careers_page": 0.45, "job_board": 0.25}
P_INTERVIEW_GIVEN_REPLY = {"referral": 0.65, "recruiter": 0.45, "careers_page": 0.55, "job_board": 0.35}
P_OFFER_GIVEN_INTERVIEW = {"referral": 0.30, "recruiter": 0.20, "careers_page": 0.20, "job_board": 0.15}
HOURS = {"referral": [2.0, 2.5, 3.0], "recruiter": [0.5, 1.0, 1.0], "careers_page": [1.0, 1.5, 2.0],
         "job_board": [0.5, 0.5, 1.0]}
COMPANIES = ["Tiffinbell", "Larkspur Coffee", "Fitloop", "Kestrel Home", "Harbor Mealkits",
             "Tidewater Outdoor", "Brightloom", "Fernhill Software", "Wrenloom", "Tallyfern",
             "Ledgerlark", "Copperwren Grocery", "Bramblequay Bikes", "Parcelwick", "Pantrywren",
             "Kettlemoor", "Brackenbee", "Learnhaven", "Larkspur Goods", "Northwind Desk"]


def iso(d):
    return "" if d is None or d > AS_OF else d.isoformat()


def build(seed=DEFAULT_SEED):
    """Return {"applications": [...]} for this seed. Nothing is written."""
    rng = random.Random(seed)
    span = (AS_OF - FIRST_DAY).days
    rows = []
    for channel, count in CHANNEL_COUNTS.items():
        for _ in range(count):
            if channel == "careers_page" and rng.random() < 0.6:
                applied = AS_OF - datetime.timedelta(days=rng.randint(1, 20))
            else:
                applied = FIRST_DAY + datetime.timedelta(days=rng.randint(0, span - 1))
            reply = interview = offer = rejected = None
            if rng.random() < P_REPLY[channel]:
                reply = applied + datetime.timedelta(days=rng.choice([1, 2, 3, 4, 5, 6, 8, 10, 13, 17, 24]))
                if rng.random() < P_INTERVIEW_GIVEN_REPLY[channel]:
                    interview = reply + datetime.timedelta(days=rng.randint(3, 10))
                    if rng.random() < P_OFFER_GIVEN_INTERVIEW[channel]:
                        offer = interview + datetime.timedelta(days=rng.randint(7, 20))
                    elif rng.random() < 0.6:
                        rejected = interview + datetime.timedelta(days=rng.randint(3, 15))
                else:
                    rejected = reply  # the first reply was a rejection
            # Anything after the pull date has not happened yet. A later stage cannot exist
            # without the earlier one.
            if reply is not None and reply > AS_OF:
                reply = interview = offer = rejected = None
            if interview is not None and interview > AS_OF:
                interview = offer = None
                if rejected is not None and rejected != reply:
                    rejected = None
            if offer is not None and offer > AS_OF:
                offer = None
            if rejected is not None and rejected > AS_OF:
                rejected = None
            rows.append({"company": rng.choice(COMPANIES), "channel": channel, "applied_on": iso(applied),
                         "reply_on": iso(reply), "interview_on": iso(interview), "offer_on": iso(offer),
                         "rejected_on": iso(rejected), "hours_spent": str(rng.choice(HOURS[channel]))})
    rows.sort(key=lambda r: (r["applied_on"], r["channel"], r["company"]))
    for i, r in enumerate(rows, 1):
        r["app_id"] = "A%02d" % i
    return {"applications": rows, "as_of": AS_OF.isoformat()}


FIELDS = ["app_id", "company", "channel", "applied_on", "reply_on", "interview_on", "offer_on",
          "rejected_on", "hours_spent"]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    d = build()
    with open(os.path.join(data, "applications.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(d["applications"])
    print("wrote", data)


if __name__ == "__main__":
    main()
