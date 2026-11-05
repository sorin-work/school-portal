# Data model

All tables are created by the Alembic migrations in `migrations/versions`.
Times are `timestamptz` in UTC, days are `date` in the school's zone.

## People and rooms

- **users**: one account per person. `role` is `admin`, `staff` or `parent`.
  `password_hash` is empty for an invited account until the invitation link
  is used. `session_version` is part of the session id; raising it signs the
  user out everywhere.
- **rooms**: a nursery room (`kind = nursery`, shows naps and nappies) or a
  school class (`kind = class`).
- **room_staff**: who works in which room, and `is_lead`.

## Children

- **children**: name, date of birth, room, key person, dietary needs,
  allergies, medical notes, `share_medical_with_parents`, `photo_consent`
  (`none`, `own`, `group`), and for leavers `left_on`, `purge_after` and
  `retention_hold`.
- **guardians**: links a parent account to a child with `relationship`,
  `access` (`full`, `read_only`, `none`), `receives_summary`, and for a
  limited link the `restriction_reason`, `restricted_by_id` and
  `restricted_at`. One row per child and account.
- **collectors**: other people who may collect a child, with an optional
  photo (`media`) and a collection password. Removing a collector sets
  `active = false` so past register rows still say who it was.

## The diary

- **events**: one row per thing that happened to one child. `kind` is one of
  `activity`, `meal`, `nap`, `nappy`, `toilet`, `mood`, `observation`,
  `incident`, `accident`, `note`. `details` (JSONB) holds what depends on the
  kind:

  | Kind | details |
  | ---- | ------- |
  | meal | `meal` (breakfast, snack, lunch, tea), `amount` (all, most, some, none), `menu` |
  | nappy | `type` (wet, dirty, dry, cream) |
  | toilet | `result` (wee, poo, tried) |
  | mood | `mood` (happy, settled, tired, unsettled, upset) |
  | activity | `title` |
  | observation | `next_steps` |
  | incident, accident | `what`, `injury`, `action_taken`, `witness` |

  A nap uses `occurred_at` and `ended_at`; an open nap has no `ended_at`.
  `visibility` is `parents` or `staff`. Events logged together share a
  `batch_id`. `area_id` links an observation to a curriculum area.
  `needs_ack`, `acknowledged_at` and `acknowledged_by_id` are for reports a
  family has to acknowledge. Removing an event sets `deleted_at`; the row
  stays for the audit trail and the subject access export.
- **curriculum_areas**: framework, code and name (the seed has the seven EYFS
  areas).
- **media**: an uploaded image: content type, size, dimensions, the stored
  file and its thumbnail. `purpose` is `photo` or `collector`.
- **event_media**: which events a photo belongs to. A group photo is one
  `media` row linked to one event per child.

## Attendance

- **attendance**: one row per child per day (unique), with arrival, going
  home, who checked them in and out, and who collected them (`collected_by`
  as text, `collector_id` when it was a collector).
- **absences**: reported ahead by a family or by staff, a date range with a
  reason. Cancelling sets `cancelled_at`.

## Communication

- **messages**: belong to a child. **message_reads** keeps, per user and
  child, the id of the last message read.
- **notifications**: per user, with a title, a local link and `read_at`.
- **notices** and **notice_rooms**: no rooms means the whole school.
- **school_events** and **school_event_rooms**: calendar entries, with
  `rsvp_required`, `consent_required`, `consent_text` and `respond_by`.
- **rsvps**: one per event and child: `attending`, `consent_given`,
  `signed_name`, `note`, who answered and when.

## Running the school

- **settings**: key and value (school name, summary time, retention days,
  idle timeout).
- **jobs**: the background queue: `kind`, `payload`, `status`, `run_at`,
  `attempts`, `last_error`, and an optional `unique_key`.
- **audit_log**: who did what to which child. `child_id` has no foreign key
  so entries survive the child's deletion.
- **password_tokens**: hashes of invitation and reset links, with expiry and
  use.
- **login_attempts**: for the sign-in rate limit, pruned after a week.
