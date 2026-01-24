"""Who may see which child, and what of it.

Every route that touches a child goes through here. The rules:

- Administrators see every child.
- Staff see the children of the rooms they work in, and their key children.
- Parents and carers see the children they are linked to as a guardian,
  unless the link's access is "none". "read_only" links see the timeline
  but cannot message, report absences or answer forms.

Lists are built from children_query(), so a child outside a user's scope is
never loaded in the first place, and single records go through child_or_404
so a guessed id gives the same 404 as a missing one.
"""

from flask import abort
from flask_login import current_user
from sqlalchemy import Select, or_, select

from .extensions import db
from .models import Child, Guardian, Room, RoomStaff, User


def staff_room_ids(user: User) -> set[int]:
    if user.is_admin:
        return set(db.session.scalars(select(Room.id)))
    if not user.is_staff:
        return set()
    return set(db.session.scalars(select(RoomStaff.room_id).where(RoomStaff.user_id == user.id)))


def lead_room_ids(user: User) -> set[int]:
    if user.is_admin:
        return staff_room_ids(user)
    return set(
        db.session.scalars(
            select(RoomStaff.room_id).where(RoomStaff.user_id == user.id, RoomStaff.is_lead)
        )
    )


def rooms_for(user: User) -> list[Room]:
    ids = staff_room_ids(user)
    if not ids:
        return []
    return list(db.session.scalars(select(Room).where(Room.id.in_(ids)).order_by(Room.sort_order)))


def children_query(user: User, *, include_left: bool = False) -> Select:
    """A select of the children this user may see, ordered by name."""
    query = select(Child).order_by(Child.first_name, Child.last_name)
    if user.is_admin:
        return query
    if user.is_staff:
        rooms = select(RoomStaff.room_id).where(RoomStaff.user_id == user.id)
        return query.where(or_(Child.room_id.in_(rooms), Child.key_person_id == user.id))
    linked = select(Guardian.child_id).where(
        Guardian.user_id == user.id, Guardian.access.in_(["full", "read_only"])
    )
    return query.where(Child.id.in_(linked))


def guardian_link(user: User, child: Child) -> Guardian | None:
    return db.session.scalar(
        select(Guardian).where(Guardian.user_id == user.id, Guardian.child_id == child.id)
    )


def can_view_child(user: User, child: Child) -> bool:
    if user.is_admin:
        return True
    if user.is_staff:
        return child.key_person_id == user.id or child.room_id in staff_room_ids(user)
    link = guardian_link(user, child)
    return link is not None and link.can_view


def can_act_for_child(user: User, child: Child) -> bool:
    """Message, report an absence, answer a form."""
    if user.is_staff:
        return can_view_child(user, child)
    link = guardian_link(user, child)
    return link is not None and link.can_act


def child_or_404(child_id: int, *, act: bool = False) -> Child:
    """Load a child the current user may see, or 404 (never 403, to not confirm ids)."""
    child = db.session.get(Child, child_id)
    if child is None:
        abort(404)
    allowed = can_act_for_child if act else can_view_child
    if not allowed(current_user, child):
        abort(404)
    return child


def can_see_medical(user: User, child: Child) -> bool:
    if user.is_staff:
        return can_view_child(user, child)
    return child.share_medical_with_parents and can_view_child(user, child)


def visible_guardians(child: Child) -> list[Guardian]:
    """Guardians who can see the child, for messages and summaries."""
    return [g for g in child.guardians if g.can_view and g.user.active]


def acting_guardians(child: Child) -> list[Guardian]:
    return [g for g in child.guardians if g.can_act and g.user.active]


def staff_for_child(child: Child) -> list[User]:
    """The key person and everyone working in the child's room."""
    users: dict[int, User] = {}
    if child.key_person is not None and child.key_person.active:
        users[child.key_person.id] = child.key_person
    if child.room is not None:
        for member in child.room.staff:
            if member.user.active:
                users[member.user.id] = member.user
    return list(users.values())
