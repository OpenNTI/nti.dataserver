Chat Protocal
=============

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


Channels
--------

Within a chat room, a 'channel' is a separate sideband of information exchange. Besides
text messages, many operational messages are carried on channels so that
they may be a part of the transcript.

Channels are named by strings, such as "DEFAULT."

Security
~~~~~~~~
Channels may be uni-directional or multi-directional. In the case of a moderated
room, each channel may have different perimissioning; in particular, permissions
may be based on the particular sender, the particular recipients, and the value
of certain fields, such as replyTo.

Interface panes
~~~~~~~~~~~~~~~
In some implementations, some channels may correspond to separate interface
"panes" or "tabs" or otherwise be displayed and interacted with differently.
(For example, the default channel may be treated like a typical chat window,
while the content channel may be used to navigate an existing browser window.)


Channels
~~~~~~~~
This section describes the defined channels. An application *MUST IGNORE*
communication on a channel it doesn't recognize.

DEFAULT
 This channel is the general any-to-all messaging channel. Messages
 on this channel, or messages that have no channel set at all, are
 delivered to all recipients in the room (regardless of the
 recipient setting). The body is uninterpreted by the server. It
 will typically be the same content as a Note (e.g., a string or a
 list of strings and Canvas objects). In moderated rooms, posts to
 this channel must be approved.

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
 is a string conforming * to the NTIID specification. The server MAY
 drop any keys in the dictionary it doesn't * recognize. Clients MUST
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
 required key is 'action;' the server and client MUST drop messages
 for unsupported actions. The remainder of the dictionary is
 action-specific; the server MAY filter out keys that are unknown
 for the particular action and the client MUST ignore them.

 The 'pin' action asks the interface to make a particular unit of content
 permanently visible. The way this is done will vary depending on content
 type. The dictionary will contain an 'ntiid' key, as for the CONTENT channel; the ID is
 more likely to be a transient ID referring to a current message in the DEFAULT channel.

 Pinned content SHOULD accumulate until the 'clearPinned' action is sent. There
 are no other keys in the body.

::

  struct MessageInfo : Object<Contained,Threadable> {
	  msgid_t ID;
	  string Creator; //May be 'System'
	  time_t LastModified; //Time of message on server.
	  msgid_t ContainerId; //The rooms to post to.
	  enum {
		  DEFAULT,
		  WHISPER,
		  CONTENT,
		  POLL,
		  META
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

Events
------

Client to Server
~~~~~~~~~~~~~~~~

For those events documented as returning something, you must request acknowledgment
of the event. The return value will be delivered in the ack to the message ID
assigned to the event. (In javascript, you need merely supply a callback function
to `emit` to make this happen; the callback will receive the return value.)

``chat_enterRoom( room_info ) -> RoomInfo``
  emit to enter a room and begin getting messages for it.

  For an anonymous (transient, person-to-person) room, the RoomId must be
  absent and the Occupants array must be present and containing
  the usernames of the online users to include in the room.
  An occupant can also be the name of a Friends List belonging to the
  user creating the room; it will be expanded by the server.
  To enter a persistent meeting room, send no Occupants, but DO
  set the ContainerId to the id of a persistent meeting container
  (for example, for a FriendsList/study group or class session, the
  id to use as the ContainerId is the 'NTIID' value)
  (If you include Occupants you may be able to start a persistent
  meeting, but you could not join one already in progress.)
  The server will reply with the enteredRoom message; its ContainerId
  will be the containerId you set (if you set one and were allowed
  to create it).

  ``chat_failedToEnterRoom( room_info )`` sent if you attempted to enter a room, but failed

``chat_exitRoom( room_id ) -> boolean``
  Emit to stop receiving messages for a room

``chat_postMessage( msg_info ) -> boolean``
  Post a message into a room. The body must be present, rooms
  must be present and should be a list of rooms to post to that you are in.
  sender should be present as well. in_reply_to should be set
  if this is a direct reply (in p2p, everything will be a direct reply)
  (use case: noticing that questions have been replied to)

  Return: whether the message was posted to all rooms

Moderation
++++++++++

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
~~~~~~~~~~~~~~~~


``chat_enteredRoom( room_info )`` and ``chat_exitedRoom( room_info )``
  Sent when you have been added to a room, directly or
  indirectly.

``chat_roomMembershipChanged( room_info )``
  Sent when a room you are in has gained/lost a member other
  than yourself.

``chat_presenceForUserChangedTo( username, presence )``
  Sent when a user in your "buddy list" goes offline/online

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
~~~~~~~~~~~

``data_noticeIncomingChange( change )``
  Sent when there is a data change, such as something
  shared with you.

::

  //Transcript access
  // Read-only
  // /prefix/Transcripts/ => { RoomId => TranscriptSummary }
  // /prefix/Transcripts/$roomId => Transcript
