"""Build the four small tables for the SQL interview lesson.

data/employees.csv  emp_id, name, department, salary
data/signups.csv    signup_id, email, signed_up_at
data/logins.csv     user_id, login_date            (several logins a day happen)
data/orders.csv     order_id, order_date, amount   (no orders at all in April 2026)

Fernhill Software is fictional. All names and emails are invented (example.com).
The data is synthetic and deterministic (fixed seed).
Run from the lesson folder: python3 make_data.py
"""
import csv
import datetime
import os
import random

random.seed(2026)

HERE = os.path.dirname(os.path.abspath(__file__))
FIRST = ["Ana", "Ben", "Chen", "Dara", "Eli", "Farah", "Gus", "Hana", "Ivo", "Jaya", "Kofi", "Lena",
         "Milo", "Nia", "Omar", "Pia", "Quinn", "Ravi", "Sara", "Teo"]
LAST = ["Abel", "Brook", "Costa", "Dunn", "Ekwueme", "Fischer", "Gill", "Hart", "Iyer", "Jones"]
DEPTS = ["Analytics", "Engineering", "Finance", "Marketing", "Sales"]


def write(name, header, rows):
    with open(os.path.join(HERE, "data", name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def employees():
    rows, used = [], set()
    for i in range(1, 37):
        while True:
            name = "%s %s" % (random.choice(FIRST), random.choice(LAST))
            if name not in used:
                used.add(name)
                break
        dept = DEPTS[(i - 1) % len(DEPTS)]
        rows.append([i, name, dept, random.randrange(60, 170) * 1000])
    rows[3][3] = 182000   # two people share the top salary
    rows[18][3] = 182000
    rows[7][3] = 175000   # second highest distinct salary
    # a tie for second place inside Finance (departments repeat every 5 rows)
    fin = [r for r in rows if r[2] == "Finance"]
    fin_sorted = sorted(fin, key=lambda r: -r[3])
    fin_sorted[2][3] = fin_sorted[1][3]
    return rows


def signups():
    rows, emails = [], []
    for i in range(1, 141):
        e = "%s.%s%d@example.com" % (random.choice(FIRST).lower(), random.choice(LAST).lower(), random.randrange(10, 99))
        emails.append(e)
    start = datetime.datetime(2026, 9, 1, 8, 0)
    sid = 1
    for e in emails:
        rows.append([sid, e, (start + datetime.timedelta(minutes=sid * 97)).strftime("%Y-%m-%d %H:%M")])
        sid += 1
    for e in random.sample(emails, 12):
        variant = random.choice([e, e.upper(), " " + e, e.capitalize()])
        rows.append([sid, variant, (start + datetime.timedelta(minutes=sid * 97)).strftime("%Y-%m-%d %H:%M")])
        sid += 1
    for e in random.sample(emails, 2):
        rows.append([sid, e, (start + datetime.timedelta(minutes=sid * 97)).strftime("%Y-%m-%d %H:%M")])
        sid += 1
    random.shuffle(rows)
    return rows


def logins():
    rows = []
    start = datetime.date(2026, 10, 1)
    for user in range(1, 41):
        p = random.choice([0.2, 0.35, 0.5, 0.7])
        for d in range(31):
            if random.random() < p:
                for _ in range(random.choice([1, 1, 2, 3])):
                    rows.append([user, (start + datetime.timedelta(days=d)).isoformat()])
    # user 41 logs in twice a day on two separate days only: a trap for the duplicate days
    rows += [[41, "2026-10-05"], [41, "2026-10-05"], [41, "2026-10-06"], [41, "2026-10-06"], [41, "2026-10-09"]]
    random.shuffle(rows)
    return rows


def orders():
    rows, oid = [], 1
    d = datetime.date(2026, 1, 1)
    while d <= datetime.date(2026, 9, 30):
        if d.month != 4 and random.random() < 0.6:
            for _ in range(random.randrange(1, 4)):
                rows.append([oid, d.isoformat(), round(random.uniform(20, 400), 2)])
                oid += 1
        d += datetime.timedelta(days=1)
    return rows


def main():
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    write("employees.csv", ["emp_id", "name", "department", "salary"], employees())
    write("signups.csv", ["signup_id", "email", "signed_up_at"], signups())
    write("logins.csv", ["user_id", "login_date"], logins())
    write("orders.csv", ["order_id", "order_date", "amount"], orders())
    print("done")


if __name__ == "__main__":
    main()
