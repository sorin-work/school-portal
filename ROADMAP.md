# Roadmap

Things I might add to school-portal. The portal covers a day in a nursery or
an infant class today (the diary, photos with consent, the register,
messages, notices, the calendar, summaries, audit, export and retention), so
nothing here is promised or scheduled. These are ideas written down with
enough detail that I, or anyone else, can pick one up later without starting
from zero. Items may change, move between groups or be dropped.

What the app does today is in the [README](README.md) and the notes under
[docs/](docs/). The honest limits are listed at the end of
[safeguarding and privacy](docs/safeguarding-and-privacy.md); most of them
have an item here.

- **Next**: small or well understood. I would start with these.
- **Later**: worth doing, but bigger or waiting on a decision.
- **Maybe**: not sure yet that they are worth the extra complexity.

Sizes are rough: **S** is an evening or two, **M** a few evenings up to a
couple of weekends, **L** several weeks of spare time.

Each item is meant to fit in one pull request and to be covered by the test
suite. There are no browser tests. `tests/unit` covers pure code
(`timeutil.py`, `photos.py`, `uploads.py`), and `tests/integration` drives
the views through Flask's test client against PostgreSQL. So logic worth
testing on its own (a ratio, a funding calculation, a retention rule) belongs
in a plain module next to `photos.py`, not inside a view. Every new child
route gets a line in `OTHER_CHILD_URLS` in `tests/integration/test_scoping.py`,
which proves a parent cannot reach another child through it. Items that add
columns bring their own migration under `migrations/versions`, and
`test_migrations.py` fails until the model and the migration agree. File
names below are relative to `school_portal/` unless they start with
`migrations/`, `tests/` or `docs/`.

"Depends on" lists real prerequisites only. Items that merely touch the same
file are not listed there; the bigger overlaps are mentioned in the items.

## Overview

| #   | Item                                            | Group | Area        | Size | Depends on |
| --- | ----------------------------------------------- | ----- | ----------- | ---- | ---------- |
| 1   | Two-factor sign-in for staff                    | Next  | security    | M    | -          |
| 2   | Retention periods per kind of record            | Next  | privacy     | M    | -          |
| 3   | Sleep checks during naps                        | Next  | diary       | S    | -          |
| 4   | Medication records                              | Next  | diary       | M    | -          |
| 5   | Import the roll from a CSV file                 | Next  | admin       | S    | -          |
| 6   | Families ask for changes to their child's details | Next | children   | M    | -          |
| 7   | Subject access in the background, and for families | Next | privacy   | M    | -          |
| 8   | Staff on shift and ratios per room              | Later | rooms       | M    | -          |
| 9   | Offline logging on tablets                      | Later | diary       | L    | -          |
| 10  | Invoicing and funded hours                      | Later | billing     | L    | -          |
| 11  | Translations                                    | Later | ui          | M    | -          |
| 12  | Progress over time per area of learning         | Later | learning    | M    | -          |
| 13  | Email and push for urgent notifications         | Later | messages    | M    | -          |
| 14  | HEIC photos, short videos and object storage    | Later | media       | M    | -          |
| 15  | Calendar feeds and paying for trips             | Later | calendar    | M    | 10         |
| 16  | Single sign-on for staff                        | Maybe | security    | M    | 1          |
| 17  | Sync with a school information system          | Maybe | admin       | L    | 5          |
| 18  | Several schools in one installation             | Maybe | ops         | L    | -          |

## Next

### 1. Two-factor sign-in for staff

Staff accounts can open every child in their rooms, medical notes included,
and an administrator can open everything. Today a password is all that stands
in front of that. The rate limit in `ratelimit.py` slows guessing down, but a
reused or phished password goes straight in.

- Data: `totp_secret` (encrypted with a key derived from `SECRET_KEY`, or a
  separate `TOTP_KEY`), `totp_enabled_at` and a `recovery_codes` table with
  hashed one-time codes, all in a new migration.
- Flow: after the password check in `blueprints/auth.py`, an account with
  two-factor on is not logged in yet; the session holds a short-lived
  "half signed in" marker and the user id, and `/login/code` asks for the
  six digits. `login_user` only runs after the code.
- Setup page under the account: a QR code (generated server-side as SVG, no
  external service) and two codes to confirm.
- Settings: "require two-factor for staff" and "for administrators". When
  required and not set up, staff land on the setup page after signing in and
  cannot open anything else.
- Tricky: shared tablets. Staff sign in on a room tablet several times a day;
  a code every time will be hated. Option: remember the device for the
  length of `SESSION_MAX_HOURS` with a signed cookie bound to the user.
- Tricky: an administrator losing their phone. Recovery codes, plus
  `flask create-admin` already resets an account from the server.
- Open question: TOTP only, or WebAuthn as well. WebAuthn is nicer on phones
  but needs HTTPS everywhere, including local development.
- Tests: sign-in stops at the code step, wrong and replayed codes, recovery
  codes work once, the requirement setting forces setup.

### 2. Retention periods per kind of record

`retention.py` deletes everything about a child after one period
(`retention_days`, three years by default). Real guidance differs per kind:
accident and incident reports are often kept until the child is 21 or older,
medication records for years, ordinary diary entries much less. One number
for all of it is either too long for the diary or too short for accidents.

- Settings: a period per kind (diary, photos, messages, attendance,
  accidents and incidents), each in months after leaving, with the age-based
  rule for accidents ("until the child turns N").
- `retention.purge_child` becomes a two-stage process: delete what is due
  and keep a slimmed record (name, date of birth, the kept reports) until the
  last kind is due. `children.purge_after` turns into "next purge date".
- The leavers page in `blueprints/admin_retention.py` shows what will go
  when.
- Tricky: a kept accident report still needs the child's name and room, so
  the child row stays; the family's accounts and links should go earlier.
- Tricky: parent accounts with no children left are never removed today.
  This item should deactivate them, and delete them after a grace period.
- Open question: whether staff-only notes count as "diary" or as
  safeguarding information with a longer period. I lean towards asking the
  school in Settings rather than guessing.
- Tests: in `tests/integration/test_retention.py`, a leaver's diary goes and
  the accident stays, then everything goes; orphaned parent accounts.

### 3. Sleep checks during naps

Nurseries check sleeping children every ten minutes or so and record it. The
room view knows who is asleep (`ChildDay.open_nap` in `events.py`) but
records only the start and the end.

- Data: a `sleep_checks` table (event id, checked at, by, position: back,
  side, front, and a note), or entries in the nap's `details`. A table keeps
  the checks queryable and the nap row small.
- Room view: the tile of a sleeping child shows minutes since the last
  check and turns amber past the room's interval; one tap records a check.
  The panel (`templates/rooms/_panel.html`) shows the list.
- Settings per room: the interval, and whether checks are required at all
  (a school class does not need them).
- Tricky: the tile needs to update without a reload; an `hx-trigger="every
  60s"` on the tiles of sleeping children is enough.
- Open question: whether families see the checks. Probably not in the
  diary, but they belong in the subject access export.

### 4. Medication records

Giving medicine in a nursery needs the parent's written permission, a record
of each dose with a witness, and the parent's signature at pick-up. None of
that is in the portal; staff use paper.

- Data: `medication_permissions` (child, medicine, dose, times or "when
  needed", from and until, given by the family through the portal) and
  `medication_doses` (permission, given at, dose, by, witnessed by).
- Families fill in the permission form themselves (full access links only,
  through `access.child_or_404(..., act=True)`).
- Staff record a dose from the child's panel; the witness confirms on the
  same tablet with their own PIN, not just a name.
- The family acknowledges each dose, reusing the acknowledgement of
  incidents (`needs_ack` on events) or a field of its own.
- Tricky: a second sign-in for the witness on a shared tablet. A short PIN
  per staff member, checked server-side, is the usual answer.
- Open question: whether a dose is also an event in the diary. I think yes,
  with `kind = "medication"`, so it shows in the timeline and the summary.

### 5. Import the roll from a CSV file

Setting up a school means typing in every child and every parent through
`blueprints/admin_children.py`. A school changing system has a spreadsheet.

- An import page for administrators: upload a CSV with one row per child and
  up to two guardians, preview what will be created and what matches an
  existing child (by name and date of birth), then confirm.
- Guardians are matched by email; new ones get the invitation from
  `_send_invite`, but only after the confirm step, and queued through
  `jobs.enqueue` so a big import does not hold the request.
- Tricky: dates in spreadsheets (`03/04/2021` is March or April). Ask for
  ISO dates, or let the administrator pick the format in the preview.
- Tricky: a bad row in the middle. All or nothing, with the list of
  problems, like the rest of the forms.
- Tests: preview counts, duplicate rows, guardians shared between siblings.

### 6. Families ask for changes to their child's details

Allergies, dietary needs and collectors change, and the family knows first.
Today they message the staff and an administrator retypes it.

- A "suggest a change" form on the child's profile
  (`templates/children/show.html`) for full access guardians: allergies,
  diet, medical notes, phone numbers, a new collector with a photo.
- Changes are stored as requests, not applied: a `change_requests` table
  with the field, the old and the new value, who asked, and the decision.
- Administrators (and optionally the key person) approve or reject; approval
  writes the change and an audit entry with the request id.
- Tricky: allergies are safety-critical. A pending change should show on the
  room tile straight away ("change pending: see profile") even before it is
  approved.
- Open question: whether a removed collector needs approval. Removing access
  is the safe direction, so it could apply at once.

### 7. Subject access in the background, and for families

`export.build_zip` runs inside the request, reads every photo into memory
and only administrators can start it. For a child with three years of
photos that is a slow request and a large response.

- Run the export as a job (`jobs.enqueue("export", ...)`) that writes the
  zip under `UPLOAD_DIR/exports`, notify the requester when it is ready, and
  serve it through an authorised route like the photos, for seven days.
- Let full access guardians request their own child's export from the
  profile. Requests by families go to an administrator to release, because
  the export may mention other people and should be read first (the page in
  `templates/exports/form.html` already says so).
- Tricky: the zip can be large; write it to disk with `zipfile` in streaming
  mode instead of `BytesIO`.
- Tests: the job builds the same contents as today's export, the download is
  refused to other families and after expiry.

## Later

### 8. Staff on shift and ratios per room

Ratios (for example one adult to three under-twos) are the first thing an
inspector asks about, and the portal knows how many children are in a room
(the register in `blueprints/attendance.py`) but not how many adults.

- Data: `staff_shifts` (user, room, started, ended), with staff signing in
  and out of a room from the room view, and moving between rooms.
- Ratios per age band in Settings, worked out from each child's date of
  birth on the day (`Child.age_on`), not from the room's name.
- The room header shows children in, adults in and the ratio, amber when it
  is close and red when it is broken; the dashboard shows every room.
- A pure function `ratio_status(children_ages, adults, rules)` in a new
  `ratios.py`, tested on its own.
- Tricky: qualified versus unqualified staff counts differ by country; keep
  the rules data, not code.
- Open question: whether a broken ratio sends a notification to the room
  lead and the manager, or only shows.

### 9. Offline logging on tablets

The room view needs the network for every tap. A garden at the far end of
the site or a trip to the park has no signal, and staff fall back to paper.

- A service worker that keeps the room view's pages, and an outbox in
  IndexedDB for posts made offline (quick logs, bulk meals, naps), replayed
  in order when the connection comes back.
- The server accepts a client id per event so a replayed post is not logged
  twice: `events.client_id` with a unique index.
- Times are taken on the device when the tap happens and sent with the post
  (the `at` field already exists in `room_view.when_from_form`).
- Tricky: what is shown offline. The tiles show the last known state plus
  what is in the outbox; a nap ended on another tablet meanwhile is a
  conflict the replay has to answer ("already ended").
- Tricky: photos offline are large. Probably text only offline, photos
  when back.
- Open question: htmx and an offline outbox do not fit well together. This
  item may mean a small amount of plain JavaScript for the room view only.

### 10. Invoicing and funded hours

Nurseries bill families for sessions and claim government-funded hours
(15 or 30 hours a week in England, term-time or stretched). It is the
reason many nurseries pick a system, and the portal has none of it.

- Data: sessions a child is booked for (patterns per weekday, with start and
  end dates), funding entitlements per child and term, price lists,
  invoices and lines, payments recorded by hand.
- Monthly invoice run as a job: booked sessions minus funded hours, extras
  (meals, late pick-up from the register's going-home time), discounts.
- Families see invoices under their account; administrators export them as
  CSV for the accounts package.
- Tricky: funding rules change every year and differ between councils.
  The calculation should be a pure module with dated rule sets and a lot of
  unit tests, not code spread through views.
- Open question: taking card payments. Out of scope at first; "paid" is
  recorded by the office.

### 11. Translations

Families in a school speak many languages; the portal is English only, in
code and in emails (`templates/email/*.txt`).

- Flask-Babel for the interface, with message catalogues under
  `translations/`, and a language preference on the user.
- Emails rendered in the recipient's language, which matters for the daily
  summary built in `summary.py`.
- Staff-written text (notes, notices) stays as written. Machine translation
  of it is a separate decision with privacy questions of its own.
- Tricky: plural forms in summaries ("Slept for 1h 15m") come from
  `Event.summary()`, which builds strings in Python; they need `ngettext`.
- Open question: which languages first, and who checks the translations.

### 12. Progress over time per area of learning

Observations are linked to an EYFS area (`events.area_id`), but nothing
reads them back: there is no view of a child's learning over a term.

- A learning journal per child: observations grouped by area, with photos,
  filterable by term; a printable view for parents' evenings.
- Optional judgements per area and term ("emerging", "expected"), recorded
  by the key person, with the observations as evidence.
- Frameworks as data: the `curriculum_areas` table already has a
  `framework` column, so Key Stage 1 subjects can be added for school
  classes.
- Tricky: photos in a journal still follow the consent rule in `photos.py`.
- Open question: whether judgements are shared with families automatically
  or released by the school at the end of a term.

### 13. Email and push for urgent notifications

Notifications live only in the app (`notify.py`), and families only get the
daily summary by email. An accident report or a message from the staff at
noon waits until the parent opens the portal.

- Per-user choices: which kinds of notification also go by email, and a
  "quiet hours" window.
- Email through the existing `queue_email`; push through the Web Push API
  for families who install the site on their phone.
- Accident reports always send an email, whatever the choices say.
- Tricky: email content. A notification email should say "there is a new
  message about Ava" and link to the portal, not include the message, so
  the email holds no details about the child.
- Open question: SMS for incidents. Costs money per message; probably a
  setting the school pays for.

### 14. HEIC photos, short videos and object storage

`uploads.py` accepts JPEG, PNG and WebP. iPhones take HEIC by default, so
staff on iPads get "only JPEG, PNG and WebP" until they change a setting.
Photos live on a local volume, which ties the app to one server.

- HEIC through `pillow-heif`, converted to JPEG on upload (still decoded and
  written again, so EXIF goes).
- Short videos (a child's first steps) with a length and size limit,
  re-encoded with ffmpeg in a job so metadata is stripped and the format is
  one browsers play.
- Storage behind a small interface (`save`, `open`, `delete`) with the
  current folder as one implementation and S3-compatible storage as
  another, served through the same authorised route or a short-lived signed
  URL issued by it.
- Tricky: signed URLs can be forwarded; keep them very short-lived and keep
  `Cache-Control: private`.
- Open question: whether videos go through the photo consent rule
  unchanged. They should, but a video of a group is harder to check.

### 15. Calendar feeds and paying for trips

The calendar in `blueprints/calendar.py` is only in the portal, and trip
consent forms mention a cost that is collected in cash.

- A private iCalendar feed per user (a long random token in the URL, which
  can be reset), with the events their children's rooms are invited to.
- Trip costs on the event, added to the family's next invoice when they say
  yes (needs item 10), or recorded as paid by the office.
- Tricky: a feed URL is a bearer token; it must not include anything about
  children, only the events.
- Open question: whether a closure in the feed should also say "your child
  has no session that day" once bookings exist.

## Maybe

### 16. Single sign-on for staff

Schools often have Microsoft 365 or Google accounts for staff. Signing in
with them would mean one less password and the school's own two-factor.

- OpenID Connect for staff only; families keep email and password.
- Accounts are matched by email and must already exist in the portal, so
  the identity provider decides who you are and the portal decides what you
  may see.
- Depends on item 1 only in the sense that the "require two-factor" setting
  should accept SSO as meeting it.
- Open question: whether this is worth it for small settings that do not
  have such accounts at all.

### 17. Sync with a school information system

Schools keep the roll in a management information system, and copying it
into the portal by hand (or even by CSV, item 5) drifts.

- A one-way, nightly import of children, classes and contacts through the
  system's API, with the CSV import's preview logic reused for the diff.
- Tricky: every system has its own API, contracts and costs; supporting one
  well is a project in itself.
- Open question: whether nurseries (the main users so far) have such a
  system at all. Most do not, which is why this is a "maybe".

### 18. Several schools in one installation

One installation is one school: settings are global and `access.py` has no
notion of a school. A group of nurseries would need one install each.

- A `schools` table and a `school_id` on rooms, children, notices, events and
  settings, with every query in `access.py` scoped by it, and staff who can
  belong to more than one school.
- Tricky: every query in the app grows a condition, and forgetting one leaks
  data between schools. The scoping tests would need a second school in the
  `school` fixture of `tests/conftest.py`.
- Open question: whether running one install per school (it is a Docker
  compose file) is simply good enough.
