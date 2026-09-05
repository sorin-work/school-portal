# Permissions

## Roles

| Role | Can |
| ---- | --- |
| Administrator | Everything: rooms, children, users, links, settings, every child's record |
| Staff | The children of the rooms they work in, and their key children in any room. Log events, run the register, message families. Room leads post notices to their rooms. |
| Parent or carer | Their own children, as far as each link allows |

An administrator also counts as staff in every room, so the room view and the
register work for them too.

## Guardian links

A parent or carer account is linked to each of their children by a
`guardians` row with an access level:

| Access | Diary and photos | Messages | Absences | Event replies and consent |
| ------ | ---------------- | -------- | -------- | ------------------------- |
| `full` | yes | read and write | report | answer |
| `read_only` | yes | read | no | no |
| `none` | no | no | no | no |

`none` exists so that a person can stay on record (and staff can see on the
profile that they must not be given information or the child) without any
access. A link with `none` makes the child invisible to that account: the
child is not in their lists and every child page answers 404.
Only an administrator can limit a link, and must give a reason; the reason,
who limited it and when are kept on the link and are shown to administrators
only.

## How it is enforced

- `access.children_query(user)` returns a select of the children a user may
  see. Every list (dashboard, messages, notices audience, calendar audience)
  starts from it, so a child outside the scope is never loaded.
- `access.child_or_404(child_id, act=False)` loads one child or answers 404.
  `act=True` also needs a `full` link for parents. It answers 404 rather than
  403 so that ids cannot be probed.
- Room pages check `access.staff_room_ids(user)`; a child id in a room URL
  must belong to that room.
- Diary events have a visibility, `parents` or `staff`. Parents get only
  `parents` events. Incident and accident reports are always `parents`.
- Medical notes are shown to staff, and to the family only when "show the
  medical notes to the family" is ticked on the child.
- Photos: see [safeguarding and privacy](safeguarding-and-privacy.md).

`tests/integration/test_scoping.py` tries every child route with a child
outside the user's scope, as a parent, as staff in another room and as an
excluded guardian.
