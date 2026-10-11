# Changelog

All notable changes, newest first. Dates are when the version was tagged.

## 0.8.0 (2026-10-11)

### Retention

- Children can be marked as left; their record is deleted after the
  retention period by the nightly job, unless it is on hold
- Group photos stay for the other children; audit entries keep the time and
  the action but lose their details
- Leavers page for administrators, with hold and delete now

### Security

- Rate limit on sign-in per address and per client
- Sessions end after a fixed time and after a period without activity
- Sign out everywhere, for yourself and by an administrator; a password
  change or reset signs out other devices
- Content-Security-Policy and other security headers on every response
- Notification polling no longer keeps an idle session alive

## 0.7.0 (2026-09-05)

- Audit log of who viewed a child's profile or diary and who changed the
  record, links, access or diary entries
- Administrators record why a guardian's access was limited, by whom and
  when
- Guardians with no access are never offered at going-home time

## 0.6.0 (2026-07-25)

- Notices for the whole school or for some rooms; room leads post to their
  own rooms
- Calendar of trips, closures and events, with replies, trip consent forms,
  a reply-by date and a CSV of the replies
- Fix: parents saw the notices of every room
- Fix: CSV cells that start like a formula are quoted

## 0.5.0 (2026-06-27)

- Email through SMTP (Mailpit in development)
- Password reset by email, and invitations for new accounts
- A job queue in the database and a worker process
- Settings page for the school name, the summary time, the retention period
  and the idle timeout
- Daily summary email to families, with a choice per child
- Account page: name, phone, password

## 0.4.0 (2026-05-30)

- Attendance register with arrival, going home and who collected
- Authorised collectors with photos and a collection password
- Absence reporting by families
- Messages per child between the family and the staff
- In-app notifications
- One register row per child and day
- Bulk logging leaves out children reported absent
- Timeline-only guardians can no longer report absences

## 0.3.0 (2026-04-11)

- Photos on learning observations, checked by type and size, with EXIF
  stripped and served only to people allowed to see them
- Photo consent per child and the group photo rule
- Incident and accident reports that the family acknowledges
- Editing and removing diary entries
- Fix: photos from phones were shown on their side

## 0.2.0 (2026-03-07)

- The room view for tablets: naps, nappies, toilet, moods and notes per
  child, meals and activities for several children at once
- The diary for families, one day at a time
- Staff-only entries
- Learning observations linked to the EYFS areas

## 0.1.0 (2026-01-24)

- Sign-in with roles: administrator, staff, parent or carer
- Rooms and classes with their staff and room leads
- Children with dietary needs, allergies and staff-only medical notes
- Parents and carers linked to children, with an access level per link
- Every page scoped to the user's children or rooms
- Demo school with `SEED_DEMO=true`
