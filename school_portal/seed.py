"""The demo school. Every person, name and photo here is invented.

Photos are drawn on the spot (coloured shapes and a label), so the demo
never contains a picture of a real child.
"""

import io
import random
from datetime import date, timedelta

from PIL import Image, ImageDraw

from . import timeutil
from .extensions import db
from .models import Child, Guardian, Role, Room, RoomStaff, User

PASSWORD = "demo-password"

STAFF = [
    # email, name, role, rooms (name, is_lead)
    ("demo@example.com", "Dana Whitfield", Role.ADMIN, []),
    ("grace.lead@example.com", "Grace Okafor", Role.STAFF, [("Acorns", True)]),
    ("tom.staff@example.com", "Tom Becker", Role.STAFF, [("Acorns", False)]),
    ("amira.lead@example.com", "Amira Hassan", Role.STAFF, [("Saplings", True)]),
    ("leo.lead@example.com", "Leo Marsh", Role.STAFF, [("Oaks", True), ("Saplings", False)]),
    ("hannah.teacher@example.com", "Hannah Price", Role.STAFF, [("Class R", True)]),
]

ROOMS = [
    ("Acorns", "nursery", "0 to 2 years", 9),
    ("Saplings", "nursery", "2 to 3 years", 12),
    ("Oaks", "nursery", "3 to 4 years", 16),
    ("Class R", "class", "Reception, 4 to 5 years", 24),
]

# first, last, preferred, age in months, room, key person email, allergies, diet, photo consent
CHILDREN = [
    ("Mila", "Nair", None, 14, "Acorns", "grace.lead@example.com", None, None, "group"),
    (
        "Theo",
        "Lindqvist",
        None,
        11,
        "Acorns",
        "tom.staff@example.com",
        "Cow's milk protein",
        "Dairy free",
        "own",
    ),
    ("Isla", "Brennan", None, 19, "Acorns", "grace.lead@example.com", None, None, "group"),
    ("Arlo", "Mensah", None, 22, "Acorns", "tom.staff@example.com", None, "Vegetarian", "none"),
    (
        "Ava",
        "Reid",
        None,
        31,
        "Saplings",
        "amira.lead@example.com",
        "Peanuts (carries an auto-injector)",
        "No nuts",
        "group",
    ),
    ("Leon", "Kowalczyk", None, 28, "Saplings", "amira.lead@example.com", None, None, "group"),
    ("Esme", "Adeyemi", None, 34, "Saplings", "leo.lead@example.com", None, "Halal", "own"),
    ("Rafi", "Doyle", None, 26, "Saplings", "amira.lead@example.com", "Egg", None, "group"),
    ("Freya", "Castellano", None, 42, "Oaks", "leo.lead@example.com", None, None, "group"),
    ("Ollie", "Pembroke", "Oliver", 45, "Oaks", "leo.lead@example.com", None, None, "group"),
    ("Zara", "Quinlan", None, 39, "Oaks", "leo.lead@example.com", "Sesame", None, "own"),
    ("Kit", "Aldridge", None, 47, "Oaks", "leo.lead@example.com", None, "Vegan", "group"),
    ("Noah", "Reid", None, 58, "Class R", "hannah.teacher@example.com", None, None, "own"),
    ("Ruby", "Okonjo", None, 55, "Class R", "hannah.teacher@example.com", None, None, "group"),
    (
        "Finn",
        "Haverford",
        None,
        61,
        "Class R",
        "hannah.teacher@example.com",
        "Hay fever",
        None,
        "group",
    ),
    (
        "Lola",
        "Szabo",
        None,
        57,
        "Class R",
        "hannah.teacher@example.com",
        None,
        "Gluten free",
        "none",
    ),
]

FAMILY_NAMES = {
    "Nair": "Priya Nair",
    "Lindqvist": "Erik Lindqvist",
    "Brennan": "Siobhan Brennan",
    "Mensah": "Kwame Mensah",
    "Kowalczyk": "Marta Kowalczyk",
    "Adeyemi": "Bisi Adeyemi",
    "Doyle": "Ciaran Doyle",
    "Castellano": "Lucia Castellano",
    "Pembroke": "James Pembroke",
    "Quinlan": "Niamh Quinlan",
    "Aldridge": "Robin Aldridge",
    "Okonjo": "Ada Okonjo",
    "Haverford": "Tess Haverford",
    "Szabo": "Gabor Szabo",
}


PALETTE = [(244, 162, 97), (42, 157, 143), (233, 196, 106), (138, 177, 125), (110, 140, 200)]


def placeholder_image(label: str, seed: int, size=(960, 720)) -> bytes:
    """A made-up 'photo': soft shapes and a caption, never a person."""
    rng = random.Random(seed)
    image = Image.new("RGB", size, PALETTE[seed % len(PALETTE)])
    draw = ImageDraw.Draw(image)
    for _ in range(9):
        x, y = rng.randint(0, size[0]), rng.randint(0, size[1])
        r = rng.randint(40, 160)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=PALETTE[rng.randrange(len(PALETTE))])
    draw.rectangle((0, size[1] - 90, size[0], size[1]), fill=(255, 255, 255))
    draw.text((30, size[1] - 70), f"Sample photo: {label}", fill=(40, 40, 40), font_size=36)
    out = io.BytesIO()
    image.save(out, "JPEG", quality=80)
    return out.getvalue()


def months_ago(today: date, months: int) -> date:
    year, month = today.year, today.month - months
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, min(today.day, 28))


def school_days(today: date, count: int) -> list[date]:
    days, day = [], today
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day -= timedelta(days=1)
    return list(reversed(days))


def seed() -> None:
    rng = random.Random(42)
    today = timeutil.today()

    users: dict[str, User] = {}
    for email, name, role, _ in STAFF:
        user = User(email=email, name=name, role=role)
        user.set_password(PASSWORD)
        db.session.add(user)
        users[email] = user

    rooms: dict[str, Room] = {}
    for order, (name, kind, ages, places) in enumerate(ROOMS):
        room = Room(name=name, kind=kind, age_range=ages, capacity=places, sort_order=order)
        db.session.add(room)
        rooms[name] = room
    db.session.flush()
    for email, _, _, memberships in STAFF:
        for room_name, lead in memberships:
            db.session.add(
                RoomStaff(room_id=rooms[room_name].id, user_id=users[email].id, is_lead=lead)
            )

    children: dict[str, Child] = {}
    for spec in CHILDREN:
        first, last, preferred, age, room, key, allergies, diet, consent = spec
        child = Child(
            first_name=first,
            last_name=last,
            preferred_name=preferred,
            date_of_birth=months_ago(today, age) - timedelta(days=rng.randint(0, 25)),
            room=rooms[room],
            key_person=users[key],
            start_date=months_ago(today, min(age - 6, 20)) if age > 8 else months_ago(today, 2),
            allergies=allergies,
            dietary_needs=diet,
        )
        db.session.add(child)
        children[first] = child
    children["Arlo"].medical_notes = "Mild eczema. Emollient cream twice a day, kept in his bag."
    children["Ava"].medical_notes = (
        "Peanut allergy. Auto-injector in the Saplings medicine box, second one in the office. "
        "Care plan reviewed in September."
    )
    children["Finn"].medical_notes = "Antihistamine on high pollen days, parent gives it at home."
    db.session.flush()

    # Families. Sam and Chris Taylor look after Ava and Noah; their father has
    # no access under a court order, which the office recorded.
    def parent(email: str, name: str, phone: str | None = None) -> User:
        user = User(email=email, name=name, role=Role.PARENT, phone=phone)
        user.set_password(PASSWORD)
        db.session.add(user)
        users[email] = user
        return user

    sam = parent("parent@example.com", "Sam Taylor", "07700 900123")
    chris = parent("gran@example.com", "Chris Taylor", "07700 900456")
    mark = parent("restricted@example.com", "Mark Reid")
    for first in ("Ava", "Noah"):
        db.session.add(Guardian(child=children[first], user=sam, relationship_label="Mother"))
        db.session.add(
            Guardian(
                child=children[first],
                user=chris,
                relationship_label="Grandparent",
                access="read_only",
                receives_summary=False,
            )
        )
        db.session.add(
            Guardian(
                child=children[first],
                user=mark,
                relationship_label="Father",
                access="none",
                receives_summary=False,
            )
        )
    priya = parent("parent2@example.com", "Priya Nair", "07700 900789")
    db.session.add(Guardian(child=children["Mila"], user=priya, relationship_label="Mother"))
    for index, (first, last, *_rest) in enumerate(CHILDREN):
        if last in ("Reid", "Nair"):
            continue
        name = FAMILY_NAMES[last]
        email = f"family{index + 1}@example.com"
        user = parent(email, name)
        db.session.add(Guardian(child=children[first], user=user, relationship_label="Parent"))
    db.session.flush()

    db.session.commit()
