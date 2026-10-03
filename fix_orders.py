"""
fix_orders.py — Fix existing orders amount & status
Run once: python fix_orders.py
"""
import sqlite3

DB = "cake_orders.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Fix status — remove "pending - ₹350" → "pending"
c.execute("SELECT id, status, cake_type, flavor, size FROM orders")
rows = c.fetchall()

CAKE_PRICES = {
    "pineapple cake": (300, 600), "black forest cake": (320, 630),
    "strawberry cake": (330, 680), "mango cake": (380, 750),
    "butter scotch cake": (330, 650), "butterscotch cake": (330, 650),
    "white forest cake": (360, 730), "chocolate truffle cake": (350, 700),
    "choco vanilla cake": (350, 680), "choco chips cake": (350, 700),
    "mix fruit cake": (360, 720), "caramel mix fruit cake": (380, 780),
    "swiss chocolate cake": (360, 700), "dutch exotic cake": (400, 800),
    "exotic black forest cake": (360, 700), "pineapple delight cake": (350, 700),
    "royal mix fruit cake": (380, 750), "premium mix fruit cake": (425, 800),
    "rasmalai cake": (500, 1000), "strawberry premium cake": (400, 750),
    "mango premium cake": (400, 800),
    "chocolate": (350, 700), "vanilla": (300, 600),
    "strawberry": (330, 680), "mango": (380, 750),
    "butterscotch": (330, 650), "black forest": (320, 630),
    "pineapple": (300, 600), "custom cake": (350, 700),
    "birthday": (350, 700), "ice cake": (350, 700),
}

def calc_price(cake_type, flavor, size):
    size_l = (size or "").lower()
    if "2" in size_l or "two" in size_l:
        mult, base = 2.0, "one"
    elif "1.5" in size_l or "half" in size_l and "1" in size_l:
        mult, base = 1.5, "one"
    elif "1" in size_l or "one" in size_l:
        mult, base = 1.0, "one"
    else:
        mult, base = 1.0, "half"

    ph, po = 350, 700
    combined = ((flavor or "") + " " + (cake_type or "")).lower()
    for key, (p_half, p_one) in CAKE_PRICES.items():
        if key in combined:
            ph, po = p_half, p_one
            break

    return int((po if base == "one" else ph) * mult)

for row in rows:
    # Fix status
    status = row["status"] or "pending"
    if "pending" in status:
        status = "pending"
    elif "confirmed" in status:
        status = "confirmed"

    # Calculate amount
    amount = calc_price(row["cake_type"], row["flavor"], row["size"])

    c.execute("UPDATE orders SET status=?, amount=? WHERE id=?",
              (status, amount, row["id"]))
    print(f"Fixed order {row['id']}: status={status}, amount=₹{amount}")

conn.commit()
conn.close()
print("\n✅ All orders fixed!")