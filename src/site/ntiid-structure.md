NTIID Tag Structure
===================

General Principles
------------------

* NTIIDs SHALL be structured as
  [RFC4151](http://www.faqs.org/rfcs/rfc4151.html) Tag URIs.
* The `authorityName` SHALL be `nextthought.com`.
* The `date` SHALL be 2011 or later. For specific NTIIDs defined in
  this document, the `date` SHALL be 2011-10.

### Mapping to HTTP ###

* Because NTIIDs MAY need to be represented concisely in HTTP URLs,
  the `specific` portion MUST NOT include any of the characters
  reverved or excluded in HTTP paths. For details see
  [rfc2396](http://www.ietf.org/rfc/rfc2396.txt) (URIs) and
  [RFC2616](http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.2.1)
  (HTTP). In brief, the characters "/", ";", "=", and "?" are
  reserved, "<", ">", "#", "%", and the single and double quote are
  excluded as delimeters, and "{", "}", "|", "\", "^", "[", "]", and
  "\`" are considered unwise for gateway reasons. Spaces are also excluded.
* When presenting an NTIID in an HTTP URL, it is presented exactly
  as-is. For example, `http://example.com/dataserver/user/pages/tag:nextthought.com,2011:AOPS-HTML-Prealgebra-0`.


Specific Portion
----------------

The meat of the specification is in the `specific` portion. The
general form of the NTIID's specific portion is:

	[Provider-]Type-TypeSpecific

The `Provider`, which is optional, is a string identifying the source
of the identified content. For example, `AOPS`. It must be unique as
of the date in the ID. The string `NTI` is reserved for us. It MAY be
a platform username.

The `Type`, which is required, specifies the type of entity pointed to
by the ID. Types may be divided into a primary type and subtypes, with
each part separated by a colon. Some initial types are defined in the
next section.

Finally, the last part, everything after the `Type` is type specific;
these are also defined in the next section. There is always a `Type`;
if there are two parts, they are `Type` and `TypeSpecific`. It is not
valid to have only a `Provider` and a `Type`.

## Types ##

### HTML ###

The `HTML` type is for identifying resources represented as HTML.
These are generally curated content, and this type MUST have a
`Provider.` This type MAY have a subtype, separated by a colon,
providing more information about the (expected) content. Examples of
subtypes include `Book` , `Chapter` and `Section`.

The type specific section is a provider-specific identifier for the
content, unique within the provider's library as of the date of
identification. One example would be `bookname-sectionnumber` for
content that came from a book. Fragment identifiers refer to fragments
of the HTML document.

A complete example is `tag:nextthought.com,2011-10:AOPS-HTML-prealgebra-0`.

### Class Rooms/Chat Rooms/Study Groups ###

The `MeetingRoom` type is for identifying resources that may contain a
collection of chat transcripts and other resources. It is used for
classrooms, persistent chat rooms, and study groups. Rooms are created
and said to be *active*. When a room is active, it may accumulate
resources and transcripts. At some future point it may be
*deactivated*, at which time no more resources can be accumulated. The
`MeetingRoom` type itself MAY have the subtypes `Class`, `ClassSection` or `Group.`

The type-specific section for a room is generally provider specific.
(And providers MUST be specified.) For a class room, it will typically
be of the form `ClassNumber.Section,` while for a study group it will
be an arbitrary name (when a study group is created from a friends
list, it will be the name of the friends list stripped of spaces and lowercased.).

The value of the fragment is unspecified. In the future, it might
identify a specific resource within the room.

An example for a class room is
`tag:nextthought.com,2011-10:OU-MeetingRoom:Section-CS1001.001` while an example for
a study group is `tag:nextthought.com:2011-10:jason@gmail.com-MeetingRoom:Group-myfriends`.


### Transcripts ###

One particularly common type of resource for a `Room` to contain is a
`Transcript,` which is a "recording" of a session of interaction
within the room. Transcripts MAY BE identified as entities for
purposes of later annotation (e.g., notes and highlights). Transcripts
are different from HTML content (they are a series of objects, not a
single document) so the mechanisms used to relate annotations to items
within a transcript will need to differ.

Transcripts have opaque, auto-generated unique identifiers. These identifiers,
while not easy to type and thus violating part of the rule for tag
URIs, make up the type-specific part. (Transcripts must represent
date and times precisely, so using the room tag plus the date and time
of creation would be possible, but equally unwieldy.) Providers are
not required.

An example identifier for a transcript is
`tag:nextthought.com,2011-10:Transcript-aoeesnthcrgf`.

Well-Known NTIIDs
-----------------

This document defines some well-known NTIIDs that have specific
purposes.

###  Root ###

The NTIID `tag:nextthought.com,2011-10:Root` is the conceptual,
virtual, root of all content on the platform. It can be said to be the
(recursive) parent of all other NTIIDs on the platform. The exact path
and depth from the root to any other NTIID is not defined, and in
general NTIIDs are not guaranteed to be structured as a tree or even a
graph (thus it is not guaranteed to be able to *walk* from the root
NTIID to all the NTIIDs it is said to contain.)

The root NTIID is useful in those circumstances where one wishes to
retrieve all data, recursively. Platform APIs that support retrieving
data recursively MAY support the virtual root or MAY require a
"physical" NTIID, but MUST document this behaviour in either case.

