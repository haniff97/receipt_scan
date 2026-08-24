import random
from datetime import datetime, timedelta

from sqlalchemy import func

from app.database import SessionLocal
from app.models import Transaction

random.seed(42)

MERCHANTS = {
    "groceries": ["Tesco", "Sainsbury's", "Aldi", "Whole Foods"],
    "dining": ["Chipotle", "Olive Garden", "Starbucks", "Local Bistro", "Panera"],
    "transport": ["Uber", "Shell Fuel", "City Metro", "BP Gas"],
    "shopping": ["Amazon", "Best Buy", "IKEA", "Target"],
    "utilities": ["Electric Co", "Water Works", "Internet Provider"],
    "entertainment": ["Netflix", "Spotify", "AMC Theatres", "Steam"],
    "health": ["CVS Pharmacy", "City Gym", "Dental Clinic"],
    "travel": ["Delta Airlines", "Airbnb", "Marriott"],
}


def make_spend(category):
    ranges = {
        "groceries": (25, 150),
        "dining": (8, 60),
        "transport": (15, 70),
        "shopping": (15, 250),
        "utilities": (40, 220),
        "entertainment": (5, 50),
        "health": (20, 120),
        "travel": (150, 600),
    }
    lo, hi = ranges[category]
    return round(random.uniform(lo, hi), 2)


def seed():
    db = SessionLocal()
    if db.query(func.count(Transaction.id)).scalar():
        print("Database already has data, skipping.")
        db.close()
        return

    now = datetime.utcnow()
    created = 0
    for days_ago in range(180, 0, -1):
        date = now - timedelta(days=days_ago)
        for _ in range(random.randint(0, 3)):
            category = random.choice(list(MERCHANTS))
            merchant = random.choice(MERCHANTS[category])
            tx = Transaction(
                date=date,
                amount=make_spend(category),
                merchant=merchant,
                category=category,
                description=f"{merchant} - {category}",
            )
            db.add(tx)
            created += 1
            if random.random() < 0.02:
                tx.amount = round(tx.amount * random.uniform(3.5, 6.0), 2)

    db.commit()
    db.close()
    print(f"Seeded {created} transactions.")


if __name__ == "__main__":
    seed()