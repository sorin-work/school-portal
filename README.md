# school-portal

A portal for a nursery or a primary school. Staff record the day as it
happens (meals, naps, nappies, moods, activities, learning observations with
photos, incidents and accidents, the register) from a tablet in the room, and
parents and carers see their own children's diary, and nothing else.

It is a Flask app with server-rendered pages, htmx for the quick logging and
PostgreSQL for everything, including the small job queue the worker runs.

## Features

- **Roles.** Administrators, staff and parents or carers. Staff work in one or
  more rooms and can be the room lead or a child's key person. A child can
  have several parents and carers.
- **Limited guardians.** Each link between a carer and a child has an access
  level: full, timeline only (no messages, absence reports or forms) or none.
  An administrator records why a link was limited, for example a court order,
  and who did it and when. Staff see on the child's profile that a person has
  no access and must not be given information or the child.
- **Rooms and children.** Nursery rooms and school classes, children with
  dietary needs, allergies and medical notes. Medical notes are staff only
  unless the family is meant to see them. Allergies show on the child's tile
  in the room view.
- **The room view.** A tablet-friendly page per room: tap a child to log a
  nap (start and end), a nappy, the toilet, a mood or a note; log a meal or
  an activity for several children at once ("everyone had lunch", with a
  different amount for the child who left half).
- **Learning observations** for one or more children, linked to an area of
  the EYFS (or any framework the school adds), with next steps.
  Up to four photos can go with each one.
- **Incidents and accidents.** A report with what happened, any injury, what
  was done and who saw it. The family always sees it, is notified and is
  asked to acknowledge it; staff see which reports are still waiting.
- **Visibility.** Every diary entry is for the family or for staff only.
- **Photo consent per child**: no photos, own family only, or group photos.
  A photo with several children is shown to a family only when every other
  child in it has group consent. Staff cannot attach photos to a child with
  no consent.
- **Uploads** are checked by what is in the file (JPEG, PNG or WebP), limited
  in size, decoded and written again so EXIF (GPS position, camera details)
  is stripped, and served only through a route that checks who is asking.
- **Attendance.** Arrival and going home from the register, with who
  collected the child.
  Authorised collectors have a photo and a collection password that staff
  see at the door.
  Parents report absences ahead, and the room's staff are told.
- **Messages** between a family and the staff, per child. There is no free
  chat.
- **Notifications** in the app for messages, reports, absences, notices and
  calendar events.
- **Notices** for the whole school or for some rooms. Room leads post to
  their own rooms.
- **Calendar** of trips, closures and events, with replies, trip consent
  forms signed by typing a name, a reply-by date and a CSV of the replies.
- **Daily summary email** to each family at a time set by the school, with
  what families may see from the day. Each carer can turn it off per child.
- **Audit log** of who viewed a child's profile or diary and who changed the
  record, links or access.
- **Retention.** A child marked as left is deleted with everything about them
  after a set period (three years by default), unless the record is on hold.
  Group photos stay for the other children.
- **Security.** Rate limits on sign-in, password reset by email, sessions
  that end after a set time and after inactivity, sign out everywhere,
  CSRF on every form and htmx request, a strict Content-Security-Policy, and
  every query scoped to the user's children or rooms.

## Quick start

With Docker:

```sh
docker compose up --build
```

Then open http://127.0.0.1:4433. Mail sent by the app (invitations,
password resets, daily summaries) lands in Mailpit at http://127.0.0.1:8033.

The compose project is called `school-portal` and uses these host ports, all
bound to 127.0.0.1:

| Service | Port |
| ------- | ---- |
| app     | 4433 |
| db      | 5463 |
| mailpit | 8033 |

## Demo logins

With `SEED_DEMO=true` (the default in `docker-compose.yml`) the first start
creates an invented school, Willow Brook Nursery and School, with four rooms,
sixteen children and their families. Every name is made up and every photo is
drawn by the seed (coloured shapes with a caption), never a real child.

All accounts use the password `demo-password`.

| Email                        | Who                                                   |
| ---------------------------- | ----------------------------------------------------- |
| `demo@example.com`           | Dana Whitfield, administrator                         |
| `amira.lead@example.com`     | Amira Hassan, room lead in Saplings                   |
| `grace.lead@example.com`     | Grace Okafor, room lead in Acorns (babies)            |
| `tom.staff@example.com`      | Tom Becker, staff in Acorns                           |
| `leo.lead@example.com`       | Leo Marsh, lead in Oaks, also works in Saplings       |
| `hannah.teacher@example.com` | Hannah Price, teacher of Class R                      |
| `parent@example.com`         | Sam Taylor, mother of Ava (Saplings) and Noah (Class R) |
| `gran@example.com`           | Chris Taylor, grandparent, timeline only              |
| `parent2@example.com`        | Priya Nair, mother of Mila (Acorns)                   |
| `restricted@example.com`     | Mark Reid, linked to Ava and Noah with no access      |

The other families have addresses like `family3@example.com` (Isla Brennan's
parent); the number is the child's place in the list in `school_portal/seed.py`.

## Configuration

Everything is read from the environment. The defaults suit local
development; `.env.example` lists them.

| Variable | Default | What it does |
| -------- | ------- | ------------ |
| `DATABASE_URL` | `postgresql+psycopg://school:school@127.0.0.1:5463/school` | The database |
| `SECRET_KEY` | `dev-secret-change-me` | Signs sessions; required when `APP_ENV=production` |
| `APP_ENV` | `development` | `production` refuses the default secret |
| `BASE_URL` | `http://127.0.0.1:4433` | Used for links in emails |
| `SCHOOL_NAME` | `School Portal` | Until a name is saved under Settings |
| `SCHOOL_TIMEZONE` | `Europe/London` | Where a day starts and ends |
| `SEED_DEMO` | `false` | Seed the demo school into an empty database |
| `SHOW_DEMO_LOGINS` | `false` | List the demo accounts on the sign-in page |
| `UPLOAD_DIR` | `./uploads` | Where photos are stored |
| `MAX_UPLOAD_MB` | `8` | Largest photo accepted |
| `SMTP_HOST`, `SMTP_PORT` | `127.0.0.1`, `1025` | Outgoing mail |
| `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TLS` | empty, empty, `false` | Mail server sign-in |
| `MAIL_FROM` | `School Portal <portal@example.com>` | Sender of every email |
| `SESSION_MAX_HOURS` | `12` | A session ends after this, active or not |
| `SESSION_COOKIE_SECURE` | `false` | Set to `true` behind HTTPS |
| `LOGIN_MAX_FAILURES` | `5` | Failed sign-ins per address before a pause |
| `LOGIN_WINDOW_MINUTES` | `15` | How long failures count |

The school name, the daily summary time, the retention period and the idle
timeout are set by an administrator under Settings and kept in the database.

## Development

You need Python 3.13, Node 22 (only to build the stylesheet) and a
PostgreSQL 17. The easiest database is the one from compose:

```sh
docker compose up -d db
python3.13 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
npm ci && npm run css        # or npm run css:watch while editing templates
alembic upgrade head
flask --app school_portal seed-demo      # optional
flask --app school_portal run --port 4433 --debug
```

Background work (email, the daily summary, the nightly housekeeping) runs in
the worker: `flask --app school_portal worker`, or `flask --app school_portal
run-jobs` to run the queue once. Without a worker, emails wait in the `jobs`
table.

An administrator for a fresh database: `flask --app school_portal create-admin`.

A new migration: change the models, then
`alembic revision --autogenerate -m "what changed"` and read what it wrote.



## Licence

MIT, see [LICENSE](LICENSE).
