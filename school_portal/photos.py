"""Which families may see a photo.

Photo consent is recorded per child:

- "none":  no photo of the child is shown to any family, not even their own.
- "own":   photos are shown to the child's own family, but only when every
           other child in the photo has "group" consent.
- "group": as "own", and the child may also appear in photos that other
           families see.

So a photo of Ava and Ben is shown to Ava's family only if Ava's consent is
not "none" and Ben's is "group", and the other way round. Staff always see
photos of the children in their scope; the rule is about families.
"""

from sqlalchemy import select

from .extensions import db
from .models import Child, Event, EventMedia


def family_may_see(own_consent: str, others_consents: list[str]) -> bool:
    if own_consent not in ("own", "group"):
        return False
    return all(consent == "group" for consent in others_consents)


def children_in(media_id: str) -> list[Child]:
    """The children a photo is attached to, through events that still exist."""
    query = (
        select(Child)
        .join(Event, Event.child_id == Child.id)
        .join(EventMedia, EventMedia.event_id == Event.id)
        .where(EventMedia.media_id == media_id)
        .distinct()
    )
    query = query.where(Event.deleted_at.is_(None))
    return list(db.session.scalars(query))


def visible_to_family_of(child: Child, tagged: list[Child]) -> bool:
    others = [c.photo_consent for c in tagged if c.id != child.id]
    return family_may_see(child.photo_consent, others)
