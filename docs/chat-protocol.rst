===============
 Chat Protocol
===============

This document outlines the objects and events used for
person-to-person and multi-person chat communication.

At a high level, once a dataserver session has been initiated, a user
can become available for chat by initiating a :ref:`"presence session"
<presence>`. (Until this is done, no other events should be delivered
from client to server.) A user can create or be invited into one or
more `Rooms`_, exchanging `Messages`_ within those rooms. Over time a
user can update his presence (change his status) and even become
unavailable for chat without terminating the dataserver session.

.. _presence:

Presence
========

RFC 6121 ("XMPP: IM And Presence"), from which this section is
inspired, `defines presence`_ as:

   The concept of presence refers to an entity's availability for
   communication over a network.  At the most basic level, presence is a
   boolean "on/off" variable that signals whether an entity is available
   or unavailable for communication (the terms "online" and "offline"
   are also used).

The definition and use of presence in this protocol follows that of
the RFC, simplified. For example, we do not (yet) support presence
subscriptions that must be approved and can be blocked (presence
information is automatically distributed to an ill-defined set of
interested parties). We also do not (yet) distinguish between the
active "resources" (sessions) of a user---a user has a single
presence, no matter how many active sessions he has open. Lastly, we
do not allow for directed presence (wherein a user can directly send a
specific presence such as "away" to a particular contact, while all
others continue to see him as available) or presence probing.

Presence information is sent from the client to the server, who then
broadcasts that presence information as needed to other clients.
Presence information is defined as this (non-Object) structure:

.. code-block:: c

	struct PresenceInfo {
		readonly string Class = "PresenceInfo";
		readonly string MimeType = "application/vnd.nextthought.presenceinfo";
		string username;
		enum {
			available,
			unavailable
		} type;

		optional enum {
			away,
			chat,
			dnd,
			xa
		} show;

		optional string status; // size limited: 140 characters
	}


The ``show`` and ``status`` members are as defined in `section 4.7.2
<http://tools.ietf.org/html/rfc6121#section-4.7.2>`_ of the RFC and
are not interpreted by the server (except that the ``status`` member may
be subject to censoring and truncation.

.. _defines presence: http://tools.ietf.org/html/rfc6121#section-4

Initial Presence
----------------

Establishing a dataserver session and a presence session are separate.
When a client first establishes a dataserver session, he is still
considered to be unavailable for purposes of this chat protocol. In
this unavailable state:

* The client MUST NOT attempt to send any chat protocol events to the
  server (other than ``chat_setPresence``).
* The client MUST discard chat protocol events it receives from the
  server (other than ``chat_setPresenceOfUsersTo``, and then only
  when one of the listed participants is the current user).
* The server SHOULD NOT send any chat protocol events to the client
  other than a single ``chat_setPresenceOfUsersTo`` event in response
  to an event from the client. In particular, the server SHOULD NOT
  allow creating chat rooms containing a session for the user.
  However, due to race conditions, propagation time and implemenattion
  lag, the server MAY generate such events.

To become available for chat purposes, the client MUST send an initial
presence event using ``chat_setPresence`` with the ``type`` key set to
the string "available." When this is received at the server, the
server will:

#. Store this presence information for that session.

   .. note::
	  As we do not distinguish between sessions, this presence
	  information will actually become the presence information
	  for all of a user's sessions.
#. Broadcast this presence information (via the
   ``chat_setPresenceOfUsersTo`` event) to the user's contacts.
#. Broadcast this presence information to the user himself.

   In this way, the user can now know that he is in the "available"
   state and is free to use the chat protocol. It also informs any
   other sessions for this user of the change in status.
#. Collect the known presence information for the user's contacts and
   send it to the user in one or more ``chat_setPresenceOfUsersTo``
   events.

   This MAY  be the same event that the user's own presence
   was reported in. This MAY or MAY NOT explicitly include the presence
   information for unavailable contacts; as the default is
   unavailable, if it is absent, the client continues to assume that
   they are unavailable.

   .. note::
	  Handling these initial updates should be exactly the same as
	  handling subsequent updates during the lifetime of the session.

Typically a client will set the user's initial presence to available
immediately following logon and creation of the dataserver session.

.. note::
   If the client does unconditionally set the presence to available
   following logon, then any previous ``show`` and ``status`` values
   set by a still-connected session will be lost. Because multiple
   sessions are allowed only for the use case of a single user moving
   between multiple devices (e.g., home and schoom comupter), and
   being active on only one device at a time, this is acceptable.

   However, should a persistent preference to *not* become available
   at login time be implemented, then a client that connects and
   chooses not to set initial presence will need a way to probe for
   what any existing session status is in order to synchronize its
   state. This requires exposing more details about separate sessions.

Updating Presence
-----------------

At any time after initially setting his presence, a user can set a new
presence using the ``chat_setPresence`` event. The server will follow
the same steps as above (with the exception of the final step,
collecting all the contact states and sending them to the user).

In an update, if either ``show`` or ``status`` is not set, it is
intpreted as its respective default value. The ``type`` member must
always be set to one of its allowed options. The server MUST reject
messages to do not conform with an error.

.. note::
   Again in the case of multiple sessions, a client MUST be prepared
   to receive presence updates for his own user, initiated by a
   session that was not his own.

Disconnecting
-------------

If the client sends a ``chat_setPresence`` event where the ``type`` is
"unavailable," the user is now effectively "offline" or invisible for
purposes of the chat protocol, but can continue to use the dataserver
session. The client MAY become active again at any time (as in
`Initial Presence`_).

The client MAY include values for ``show`` and ``status`` when it
becomes unavailable. The server MUST broadcast these values (if any)
to the users contacts. However, the server is NOT required to store
these values persistently for reporting to contacts in the future,
regardless of whether the user's session is still connected.

Before terminating the user's session, the client SHOULD set his
presence to unavailable. When the session disconnects, the server MUST
detect whether the user's presence was available at the time of
disconnection (meaning that the client failed to disconnect). If so,
the server MUST broadcast an unavailable presence to the user's contacts.


Rooms
=====

Chats are organized into rooms.

.. code-block:: c

  //Chat server info
  typedef string roomid_t;
  typedef string msgid_t;

  struct RoomInfo : Object<Contained,Threadable> {
	  roomid_t ID;
	  time_t CreatedTime;
	  boolean Active;
	  int MessageCount;
	  boolean Moderated;
	  //Am I being shadowed in this room?
	  //if so, all of my non-default-channel posts
	  //and messages I receive will be copied to someone else
	  boolean Shadowed;

	  string[] Occupents;
	  //If the room is moderated, this will be the list of names of those that are moderating.
	  string[] Moderators;
  }


Messages
========

Once a room is established, occupants of the room (and in some cases,
non-occupants and the system) communicate by sending *messages* to the
room (see the events defined below).

Within a chat room, a 'channel' is a separate sideband of information
exchange. Besides text messages, many operational messages are carried
on channels so that they may be a part of the transcript.

Channels are named by strings, such as "DEFAULT."

.. code-block:: c

  struct MessageInfo : Object<Contained,Threadable> {
	  msgid_t ID;
	  string Creator; //May be 'System'
	  time_t LastModified; //Time of message on server.
	  msgid_t ContainerId; //The room to post to.
	  enum {
		  DEFAULT,
		  WHISPER,
		  CONTENT,
		  POLL,
		  META,
		  STATE
	  } channel;

	  enum {
		  st_PENDING,
		  st_POSTED,
		  st_SHADOWED,
		  st_INITIAL
	  } Status;

	  msgid_t inReplyTo; //parent message id.
	  Object body; //See info on channels to determine the body.

	  //A list of usernames that should get this message.
	  //Only important if on the non-default channel.
	  string[] recipients;
  }

  struct TranscriptSummary : Object {
	  readonly RoomInfo RoomInfo;
	  //set of all usernames that received or sent messages
	  //contained in this transcript
	  readonly string[] Contributors;
  }

  struct Transcript : TranscriptSummary {
	  MessageInfo Messages[];
  }


Security
--------
Channels may be uni-directional or multi-directional. In the case of a moderated
room, each channel may have different perimissioning; in particular, permissions
may be based on the particular sender, the particular recipients, and the value
of certain fields, such as replyTo.

Interface panes
---------------
In some implementations, some channels may correspond to separate interface
"panes" or "tabs" or otherwise be displayed and interacted with differently.
(For example, the default channel may be treated like a typical chat window,
while the content channel may be used to navigate an existing browser window.)


Channels
--------
This section describes the defined channels. An application *MUST IGNORE*
communication on a channel it doesn't recognize.

DEFAULT
	This channel is the general any-to-all messaging channel. Messages
	on this channel, or messages that have no channel set at all, are
	delivered to all recipients in the room (regardless of the
	recipient setting). The body has the same content as a Note (e.g.,
	a string or a list of strings and Canvas objects). In moderated
	rooms, posts to this channel must be approved.
WHISPER
	This channel is for messages directed from one user to a subset of
	the other users in the room. (For moderation, if the recipient list
	is the full list of room occupants excluding moderators, this is
	the same as the DEFAULT channel.) The use-case is for private
	conversations between students and assistants. Users may have their
	whispers shadowed by a moderator, meaning that all conversation to
	or from that user on the whisper channel is echoed to the
	moderator. In moderated rooms, the ability to whisper may be
	restricted to particular recipients (TAs). The body is as for the
	DEFAULT channel.
CONTENT
	This channel is used to ask recipients to display particular units
	of content. The content is displayed in the way most suitable for
	that content, and replaces previous content like that. The content
	is typically curated content. In moderated rooms, the ability to
	send on this channel may be restricted to particular senders.

	The body is a dictionary. One key is defined, 'ntiid', whose value
	is a string conforming to the NTIID specification. The server MAY
	drop any keys in the dictionary it doesn't recognize. Clients MUST
	ignore unknown keys. The recipients list is ignored and this message
	goes to all occupants.
POLL
	This channel contains interactive quizzes/assessments and, probably
	most common, student polls. When a message is posted without a
	replyTo set (a privilege restricted to moderators in moderated
	rooms) then its body is a dictionary of polling options (TBD). When
	a replyTo is set on a message that's posted, it is a response to a
	poll (a privilege open to anyone in moderated rooms)--and it must
	refer to a poll; the server MAY drop messages that do not refer to
	polls on this channel. Messages on the DEFAULT or WHISPER channels
	MAY be inReplyTo polls to discuss them. Recipient lists are ignored
	and this message goes to all occupants.
META
	This channel is used for meta information and meta commands that
	affect other channels. In particular, it is used to request
	interfaces to pin particular messages. In moderated rooms, this
	channel will be restricted to sending by moderators only. Recipient
	lists are ignored and commands are distributed to all occupants

	The body is a dictionary describing the command. One key is always
	'channel', naming the channel to apply the action to. The server
	and client MUST drop messages for unsupported channels. Another
	required key is 'action;' the server and client *MUST* drop messages
	for unsupported actions. The remainder of the dictionary is
	action-specific; the server MAY filter out keys that are unknown
	for the particular action and the client MUST ignore them.

	The 'pin' action asks the interface to make a particular unit of
	content permanently visible. The way this is done will vary
	depending on content type. The dictionary will contain an 'ntiid'
	key, as for the CONTENT channel; the ID is more likely to be a
	transient ID referring to a current message in the DEFAULT
	channel.

	Pinned content *SHOULD* accumulate until the 'clearPinned' action is
	sent. There are no other keys in the body.
STATE
	The state channel is used for communicating the human user's
	interaction status with the chat room. Clients will post messages
	containing these events to the server, and the server, at its sole
	discretion, will choose to forward these messages to other
	occupants of the room, or drop them. (In particular, they *MAY* be
	dropped in multi-occupants chats.) Messages on this channel *do
	not* go to the transcript.

	The body consists of a dictionary with one defined key,
	``state``. The values for this key are strings from the
	following list: "active," "composing," "paused," "inactive,"
	and "gone." (Any unknown keys are dropped.)

	Initially, when an occupant enters a room, he is defined to be
	in the state "active" (that first notice is implicit or
	assumed by the client; in other words, 'active' is the
	default, initial state of a new room occupant). The recipt of
	any message on any channel from a particular occupant also
	sets his (the sender's) state to "active" for the receiving
	client (thus clearing any "composing" or "inactive" states,
	for example). (The server will never send a state transaction
	by itself, and in particular will never send an "active" state
	transition. The sending of "active" states by clients should
	be rare; the two implicit transitions defined above should
	minimize the need to send "active" states, thus reducing load
	for all parties.)

	The description here borrows heavily from the Jabber protocol:
	`XMPP-0085: Chat State Notifications
	<http://xmpp.org/extensions/xep-0085.html>`_. Implementations
	should generally follow that specification for when and how to
	generate notices (see Table 1) where it doesn't conflict with
	this specification. One rule of particular importance is that
	the client *MUST NOT* generate multiple state events of the
	same type consecutively. That is, if the client sends a
	"composing" notice, then it must not send another "composing"
	notice without sending an intervening notice. (Since receiving
	a message places the occupant (sender) into the "active"
	state, and occupants receive their own messages, then
	transitioning from "composing" to "active" after sending a
	message should be automatic, and the transition to "composing"
	with its accompanying broadcast should then be allowed again.)

	Clients are responsible for tracking their own current state and
	the state of any other occupants in the room if they are
	interested; the server will not maintain this information.


Events
======

Client to Server
----------------

``chat_setPresence(presence)``
  Set the presence of the user, as described in `Presence`_. The
  client MUST send one of these events (and await its response) before
  using other chat events. There is no defined return value.

``chat_enterRoom( room_info ) -> RoomInfo``
  emit to enter a room and begin getting messages for it.

  For an anonymous (transient, person-to-person) room, the RoomId *MUST* be
  absent and the Occupants array *MUST* be present and containing
  the usernames of the online users to include in the room.
  An occupant can also be the name of a FriendsList belonging to the
  user creating the room; it will be expanded by the server.

  To enter a persistent meeting room, send no Occupants, and no
  RoomId, but DO set the ContainerId to the id of a persistent meeting
  container (for example, for a FriendsList/study group or class
  session, the id to use as the ContainerId is the 'NTIID' value) (If
  you include Occupants you may be able to start a persistent meeting,
  but you could not join one already in progress.) For more on the
  policies around persistent meeting rooms, see
  :py:mod:`nti.dataserver.meeting_container_storage`.

  If you send a RoomId, it *SHOULD* refer to an existing meeting room
  that is active and containing other occupants. If you were
  previously an occupant of this room, you will rejoin the room. The
  RoomId takes precedence over any other value (such as ContainerId or
  Occupants.)

  The server will reply with the ``chat_enteredRoom`` message; its ContainerId
  will be the containerId you set (if you set one and were allowed
  to create it). If something goes wrong, the server will reply with
  the ``chat_failedToEnterRoom`` message.

``chat_exitRoom( room_id ) -> boolean``
  Emit to stop receiving messages for a room. Other occupants of the
  room will receive the ``chat_roomMembershipChanged`` message.

``chat_postMessage( msg_info ) -> boolean``
  Post a message into a room. The body must be present, rooms
  must be present and should be a list of rooms to post to that you are in.
  sender should be present as well. in_reply_to should be set
  if this is a direct reply (in p2p, everything will be a direct reply)
  (use case: noticing that questions have been replied to)

  Return: whether the message was posted to all rooms

``chat_addOccupantToRoom( room_id, occupant ) -> boolean``
  Request that the server add the (online) occupant name
  to the identified room. You must be permitted to
  do this (currently, that means only the creator of the room, and the room must
  not be persistent).

  As a special condition, if the occupant was previously in the room
  but has left, the occupant will not be added again. This prevents
  abuse and annoyance (at least until we have finer grained presence
  controls).

  If the occupant was added to the room, he will receive the
  ``chat_enteredRoom`` message. All other occupants will get the
  ``chat_roomMembershipChanged`` message. The new occupant will only
  have access to the transcript for messages that arrive after he was
  added.

  The return value's truth value indicates whether or not the user was
  added to the room.

Moderation
~~~~~~~~~~

``chat_approveMessages( mid[] )``
  Cause the messages to be approved.

``chat_makeModerated( room_id, flag ) -> RoomInfo``
  The returned RoomInfo will either list you as a moderator,
  or not.

``chat_shadowUsers( room_id, usernames[] ) -> boolean``
  Causes all messages on non-default channels to be sent
  to all room moderators via recvMessageForShadow

``chat_flagMessagesToUsers( mid[], usernames[] ) -> boolean``
  Causes each user to get recvMessageForAttention


Server to client
----------------

``chat_presenceOfUsersChangedTo( presence_dict )``
  Sent when one of your contacts (or one of our own sessions) changed
  presence information. The argument is a dictionary mapping usernames
  to presence objects.

``chat_enteredRoom( room_info )`` and ``chat_exitedRoom( room_info )``
  Sent when you have been added/removed from a room, directly or
  indirectly.

``chat_failedToEnterRoom( room_info )``
  sent if you attempted to enter a room, but failed

``chat_roomMembershipChanged( room_info )``
  Sent when a room you are in has gained/lost a member other
  than yourself.

``chat_roomModerationChanged( room_info )``
  Sent when a room you are in has a change in moderation status, such
  as becoming moderated or gaining a moderator. Note that you will
  recieve this after you call ``chat_makeModerated`` (you may receive
  it multiple times with slightly different states, such as Moderated
  being true, but no moderators listed, and then again with Moderated
  as true and with moderators listed).

``chat_presenceOfUserChangedTo( username, presence )``
  **[DEPRECATED]** Sent when a user in your "buddy list" goes offline/online. The
  currently defined values for ``presence`` are the strings "Online"
  and "Offline."

``chat_recvMessage( msg_info )``
  A message arrived in a room you are currently in.
  This includes messages you yourself posted.
  This may be sent multiple times if the message is edited (for instance,
  moderated); compare by message id.

``chat_recvMessageForModeration( msg_info )``
  Sent to the moderators of a room when a message arrives
  that requires moderation

``chat_recvMessageForAttention( mid )``
  Sent to someone in a room when a message requires their attention.

``chat_recvMessageForShadow( msg_info )``
  Sent to the moderators of a room when a shadowed user
  posts or receives something on a non-default channel.

Data Events
-----------

``data_noticeIncomingChange( change )``
  Sent when there is a data change, such as something
  shared with you.

::

  //Transcript access
  // Read-only
  // /prefix/Transcripts/ => { RoomId => TranscriptSummary }
  // /prefix/Transcripts/$roomId => Transcript
