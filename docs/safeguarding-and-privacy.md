# Safeguarding and privacy

The portal holds information about young children: health, behaviour,
photos, who may collect them. This page says what it does to protect that
and, as plainly, what it does not do. It is not legal advice; a school using
it still needs its own data protection impact assessment and policies.

## Who sees what

See [permissions](permissions.md). In short: families see only their own
children and only entries marked for families; staff see only the rooms they
work in and their key children; every child route answers 404 outside that
scope.

## Excluded and limited guardians

A court order or a safeguarding plan can mean a parent must not get
information about a child or collect them. An administrator sets that
person's link to "no access" and records the reason. The child then
disappears from that account completely, the person is not offered at
going-home time, and staff see on the child's profile, in red, that this
person has no access. The reason itself (for example a case reference) is
shown to administrators only.

What the portal cannot do is stop someone at the door: staff still have to
check who is collecting. The collection password and the collector photos
are there to help with that.

## Photos and consent

Each child has a photo consent recorded from the family's form:

- **No photos shared**: staff cannot attach a photo to an observation about
  this child, and no family sees a photo of them.
- **Own family only**: the family sees photos of their child, but only
  photos in which every other child has group consent.
- **Group photos allowed**: the child may appear in photos that other
  families see.

The rule is checked when a photo is shown, not when it is taken, so a change
of consent applies to old photos too. A photo is tagged with children
through their observations; if staff remove a child's observation, that
child no longer counts for the photo.

Uploaded images are decoded and written again before they are stored. That
drops EXIF data (GPS position, time, camera serial) and anything else hidden
in the file. Only JPEG, PNG and WebP are accepted, up to `MAX_UPLOAD_MB`.
Files are served only through a route that checks the viewer, with
`Cache-Control: private`.

The seed's photos are drawn by code. Nothing in this repository is a picture
of a real child.

## Incidents and accidents

Reports are always visible to the family, who are notified and asked to
acknowledge them. Staff see a list of reports still waiting. The portal is
not a safeguarding record: concerns about a child's welfare go to the
designated safeguarding lead through the school's own process, and the
incident form says so.

## Audit

Staff opening a child's profile or diary, and every change to a child, a
link, an access level, a collector or a diary entry, is written to the audit
log with the time, the person and their IP address. Views by the same person
are recorded once per half hour. Administrators can read the log per child.
Families looking at their own children are not logged.

## Subject access

An administrator can download a child's whole record as a zip: details,
every diary entry (including staff-only and removed ones, marked as such),
attendance, absences, messages, event replies, and the photos the family may
have under the consent rules. Photos left out are counted. The export may
still mention other people (other children's first names in an observation,
staff names) and should be read and redacted before it is handed over.

## Retention

When a child leaves, an administrator marks the last day. The record is then
deleted after the retention period (Settings, three years by default) by the
nightly job, with everything about the child: diary, photos only they are
in, messages, attendance, links. Group photos stay for the other children.
Earlier audit entries keep their time and action but lose their details, and
one entry records the deletion. A record can be put on hold, for example
while a complaint or a claim is open.

One period for everything is a simplification: accident records in
particular are often kept much longer than the rest. See the roadmap.

## Sessions and sign-in

Passwords are hashed with scrypt. Sign-in is limited per address and per
client. Sessions end after `SESSION_MAX_HOURS` and after the idle timeout
(Settings), which matters on shared tablets. Changing or resetting a password
signs out every other device, and a user or an administrator can sign a
person out everywhere. Reset and invitation links are single use, stored
only as hashes, and expire after an hour (resets) or a week (invitations).

## What is not done

- No two-factor sign-in, not even for staff.
- No encryption of the database or the photo folder by the app; that is left
  to the disk and the hosting.
- No virus scanning of uploads (they are images that are decoded and written
  again, which removes most of the risk, but not all).
- Backups are not part of the app.
