"""The demo school. Every person, name and photo here is invented.

Photos are drawn on the spot (coloured shapes and a label), so the demo
never contains a picture of a real child.
"""

import io
import random
from datetime import date, time, timedelta

from PIL import Image, ImageDraw

from . import settings, timeutil
from .extensions import db
from .models import (
    Absence,
    Attendance,
    Child,
    Collector,
    CurriculumArea,
    Event,
    EventMedia,
    Guardian,
    Media,
    Message,
    Role,
    Room,
    RoomStaff,
    User,
)
from .models.media import new_media_id

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

EYFS = [
    ("EYFS-CL", "Communication and language"),
    ("EYFS-PD", "Physical development"),
    ("EYFS-PSED", "Personal, social and emotional development"),
    ("EYFS-L", "Literacy"),
    ("EYFS-M", "Mathematics"),
    ("EYFS-UW", "Understanding the world"),
    ("EYFS-EAD", "Expressive arts and design"),
]

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
    settings.put("school_name", "Willow Brook Nursery and School")

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
            photo_consent=consent,
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

    db.session.add(
        Collector(
            child=children["Ava"],
            name="Jo Marlow",
            relationship_label="Childminder",
            phone="07700 900321",
            password_hint="blue kite",
            photo=_photo(
                "Collector Jo Marlow", 501, users["demo@example.com"], purpose="collector"
            ),
        )
    )
    db.session.add(Collector(child=children["Mila"], name="Anil Nair", relationship_label="Uncle"))
    areas = []
    for order, (code, name) in enumerate(EYFS):
        area = CurriculumArea(framework="EYFS", code=code, name=name, sort_order=order)
        db.session.add(area)
        areas.append(area)
    db.session.flush()

    _seed_days(rng, today, rooms, children, users)
    _seed_observations(today, rooms, children, users, areas)
    _seed_incidents(today, rooms, children, users)
    _seed_messages(today, children, users)
    db.session.commit()


def _photo(label: str, seed_value: int, user: User, purpose: str = "photo") -> Media:
    from .uploads import _write, clean_image

    cleaned = clean_image(placeholder_image(label, seed_value), 20 * 1024 * 1024)
    media_id = new_media_id()
    stored = f"{media_id[:2]}/{media_id}.{cleaned.ext}"
    thumb = f"{media_id[:2]}/{media_id}.thumb.{cleaned.ext}"
    import os

    from flask import current_app

    os.makedirs(os.path.join(current_app.config["UPLOAD_DIR"], media_id[:2]), exist_ok=True)
    _write(stored, cleaned.data)
    _write(thumb, cleaned.thumb)
    media = Media(
        id=media_id,
        purpose=purpose,
        content_type=cleaned.content_type,
        size=len(cleaned.data),
        width=cleaned.width,
        height=cleaned.height,
        stored_name=stored,
        thumb_name=thumb,
        uploaded_by_id=user.id,
    )
    db.session.add(media)
    return media


MENUS = {
    "breakfast": "Porridge with banana",
    "snack": "Apple slices and rice cakes",
    "lunch": "Vegetable lasagne and peas",
    "tea": "Jacket potato and beans",
}

ACTIVITIES = {
    "Acorns": [
        "Treasure basket",
        "Messy play with jelly",
        "Singing time",
        "Garden walk in the buggies",
    ],
    "Saplings": [
        "Painting with leaves",
        "Building towers",
        "Story time: The Gruffalo",
        "Water play",
    ],
    "Oaks": ["Planting cress", "Obstacle course", "Counting conkers", "Role play shop"],
    "Class R": ["Phonics: the sh sound", "Number bonds to ten", "PE: ball skills", "Forest school"],
}


def _seed_days(rng, today, rooms, children, users) -> None:
    staff_by_room = {
        "Acorns": users["grace.lead@example.com"],
        "Saplings": users["amira.lead@example.com"],
        "Oaks": users["leo.lead@example.com"],
        "Class R": users["hannah.teacher@example.com"],
    }
    now = timeutil.now()
    for day in school_days(today, 6):
        is_today = day == today
        for child in children.values():
            room = child.room
            by = staff_by_room[room.name]
            if is_today and child.first_name == "Isla":
                continue

            def at(hour, minute, _day=day):
                return timeutil.at(_day, time(hour, minute))

            def add(
                kind,
                when,
                details=None,
                note=None,
                visibility="parents",
                ended=None,
                *,
                _child=child,
                _room=room,
                _by=by,
            ):
                if when > now:
                    return None
                event = Event(
                    child_id=_child.id,
                    room_id=_room.id,
                    kind=kind,
                    occurred_at=when,
                    ended_at=ended if ended is None or ended <= now else None,
                    details=details or {},
                    note=note,
                    visibility=visibility,
                    created_by_id=_by.id,
                )
                db.session.add(event)
                return event

            arrive = at(8, rng.randint(0, 45))
            if arrive <= now:
                leave = at(16, rng.randint(30, 59)) if not is_today else None
                collected = None
                if leave is not None:
                    guardian = child.guardians[0].user.name if child.guardians else "Parent"
                    collected = guardian
                db.session.add(
                    Attendance(
                        child_id=child.id,
                        room_id=room.id,
                        day=day,
                        checked_in_at=arrive,
                        checked_in_by_id=by.id,
                        checked_out_at=leave,
                        checked_out_by_id=by.id if leave else None,
                        collected_by=collected,
                    )
                )
            add("mood", at(9, 5), {"mood": rng.choice(["happy", "settled", "settled", "tired"])})
            if room.name != "Class R":
                add(
                    "meal",
                    at(9, 30),
                    {
                        "meal": "snack",
                        "amount": rng.choice(["all", "most"]),
                        "menu": MENUS["snack"],
                    },
                )
            add(
                "meal",
                at(11, 45),
                {
                    "meal": "lunch",
                    "amount": rng.choice(["all", "most", "some"]),
                    "menu": MENUS["lunch"],
                },
            )
            if room.is_nursery and room.name != "Oaks":
                start = at(12, 30 + rng.randint(0, 20))
                add("nap", start, ended=start + timedelta(minutes=rng.randint(45, 110)))
                for hour in (10, 13, 15):
                    add(
                        "nappy",
                        at(hour, rng.randint(0, 50)),
                        {"type": rng.choice(["wet", "wet", "dirty", "dry"])},
                    )
            elif room.name == "Oaks":
                add("toilet", at(10, 40), {"result": rng.choice(["wee", "tried"])})
            if room.name != "Class R":
                add(
                    "meal",
                    at(15, 30),
                    {
                        "meal": "tea",
                        "amount": rng.choice(["all", "most", "some"]),
                        "menu": MENUS["tea"],
                    },
                )
            title = ACTIVITIES[room.name][day.toordinal() % 4]
            add("activity", at(10, 15), {"title": title})
        # A staff-only note: families never see it.
        if not is_today or timeutil.now() > timeutil.at(day, time(14, 0)):
            db.session.add(
                Event(
                    child_id=children["Theo"].id,
                    room_id=rooms["Acorns"].id,
                    kind="note",
                    occurred_at=timeutil.at(day, time(14, 0)),
                    note="Unsettled after drop-off, settled with his comforter. Keep an eye on it.",
                    visibility="staff",
                    created_by_id=users["tom.staff@example.com"].id,
                )
            )
    db.session.add(
        Absence(
            child_id=children["Isla"].id,
            start_date=today,
            end_date=today + timedelta(days=1),
            reason="illness",
            note="Temperature last night, keeping her at home.",
            reported_by_id=users["family3@example.com"].id,
        )
    )


def _seed_observations(today, rooms, children, users, areas) -> None:
    yesterday = school_days(today, 2)[0]
    by_code = {a.code: a for a in areas}
    items = [
        # children, room, area code, note, next steps, photo label (None for no photo)
        (
            ["Ava", "Leon"],
            "Saplings",
            "EYFS-PSED",
            "Ava and Leon took turns pouring water between the jugs and counted the pours together.",
            "More turn-taking games with a timer.",
            "Water play",
        ),
        (
            ["Esme"],
            "Saplings",
            "EYFS-CL",
            "Esme told the group about her weekend using sentences of four or five words.",
            "Encourage her to ask questions at story time.",
            None,
        ),
        (
            ["Freya", "Ollie", "Kit"],
            "Oaks",
            "EYFS-UW",
            "Planted cress in eggshells, talked about what seeds need to grow.",
            "Check the cress on Monday and measure it.",
            "Cress planting",
        ),
        (
            ["Noah"],
            "Class R",
            "EYFS-L",
            "Noah read a decodable book aloud and blended sh words without help.",
            "Move to the next phonics book band.",
            "Reading corner",
        ),
        (
            ["Mila"],
            "Acorns",
            "EYFS-PD",
            "Mila pulled herself up on the low shelf and took three steps along it.",
            "Push-along toys in the garden.",
            "Cruising along the shelf",
        ),
        (
            ["Zara", "Freya"],
            "Oaks",
            "EYFS-EAD",
            "Zara and Freya made a shop sign and priced the fruit at 1p and 2p.",
            None,
            "Role play shop",
        ),
    ]
    for index, (names, room_name, code, note, steps, label) in enumerate(items):
        day = yesterday if index % 2 == 0 else today
        when = timeutil.at(day, time(10, 30 + index * 4))
        if when > timeutil.now():
            when = timeutil.at(yesterday, time(10, 30 + index * 4))
        by = rooms[room_name].leads[0] if rooms[room_name].staff else users["demo@example.com"]
        media = _photo(label, 100 + index, by) if label else None
        for name in names:
            event = Event(
                child_id=children[name].id,
                room_id=rooms[room_name].id,
                kind="observation",
                occurred_at=when,
                note=note,
                details={"next_steps": steps} if steps else {},
                visibility="parents",
                area_id=by_code[code].id,
                created_by_id=by.id,
            )
            if media is not None:
                event.photos.append(EventMedia(media=media))
            db.session.add(event)


def _seed_incidents(today, rooms, children, users) -> None:
    days = school_days(today, 3)
    old = Event(
        child_id=children["Leon"].id,
        room_id=rooms["Saplings"].id,
        kind="accident",
        occurred_at=timeutil.at(days[0], time(14, 10)),
        note="Tripped on the edge of the rug and bumped his forehead on the table.",
        details={
            "what": "Tripped on the edge of the rug and bumped his forehead on the table.",
            "injury": "Small red mark above the right eyebrow, no swelling",
            "action_taken": "Cold compress for ten minutes, watched for the rest of the afternoon.",
            "witness": "Amira Hassan",
        },
        visibility="parents",
        needs_ack=True,
        acknowledged_at=timeutil.at(days[0], time(17, 5)),
        acknowledged_by_id=children["Leon"].guardians[0].user_id,
        created_by_id=users["amira.lead@example.com"].id,
    )
    db.session.add(old)
    when = timeutil.at(days[-1], time(10, 50))
    if when > timeutil.now():
        when = timeutil.at(days[-2], time(10, 50))
    db.session.add(
        Event(
            child_id=children["Ava"].id,
            room_id=rooms["Saplings"].id,
            kind="accident",
            occurred_at=when,
            note="Slipped on the wet patio during water play and grazed her knee.",
            details={
                "what": "Slipped on the wet patio during water play and grazed her knee.",
                "injury": "Graze on the left knee",
                "action_taken": "Cleaned with water and a wipe, plaster on. Back to playing after a cuddle.",
                "witness": "Leo Marsh",
            },
            visibility="parents",
            needs_ack=True,
            created_by_id=users["amira.lead@example.com"].id,
        )
    )


def _seed_messages(today, children, users) -> None:
    base = timeutil.at(school_days(today, 2)[0], time(7, 40))
    thread = [
        (
            users["parent@example.com"],
            "Morning! Ava was up in the night with a cough, she might be tired today.",
        ),
        (
            users["amira.lead@example.com"],
            "Thanks for letting us know. We'll keep her nap at the usual time and tell you how she gets on.",
        ),
        (
            users["amira.lead@example.com"],
            "She slept for an hour and a half and was much brighter after.",
        ),
        (users["parent@example.com"], "That's great, thank you."),
    ]
    for offset, (author, body) in enumerate(thread):
        db.session.add(
            Message(
                child_id=children["Ava"].id,
                author_id=author.id,
                body=body,
                created_at=base + timedelta(hours=offset * 3),
            )
        )
    db.session.add(
        Message(
            child_id=children["Mila"].id,
            author_id=users["parent2@example.com"].id,
            body="Could you try her with the new beaker at lunch? She has started using one at home.",
            created_at=base + timedelta(hours=1),
        )
    )
