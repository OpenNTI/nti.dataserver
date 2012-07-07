Content Types
=============

This document describes the foundational content types supported for
storage with the dataserver. Specific content types that are used only
in certain other areas may be addressed specifically in those
documents, but will generall reference definitions established here.

The content types are described in a C-like IDL, but recall that they
are represented on the wire as either JSON or PList. In general,
however, the field names will be the same.

Basics
------

We begin with some basic definitions that are shared throughout.
First, note that *most* content types exchanged with the dataserver
extend from a defined ``Object`` type (so they inherit all the fields
of an ``Object.`` A few things are defined not to need the overhead
and flexibility added by being an ``Object`` and do not inherit these
fields; in general, if something can be used in a standalone fashion,
it will inherit from ``Object,`` otherwise, if it is always nested and
contained within another object, it may not. (Regardless of this, the
general term "object" is used throughout this document.)

Next, conventions that are followed. In general, fields which are
capitalized are immutable once set. Fileds named with a lowercase
letter are subject to modification once an object is created. Arrays
that are empty may be omitted entirely (however, some types will
have different rules for the treatment of missing data.)

We begin by defining the root ``Object``:

.. code-block:: cpp


   typedef string ntiid;
   typedef string oid_t;

   struct Link {
	   // A link represents a relationship between two entities.
	   // One entity is defined by being the container of the link.
	   // The other entity is specified as the target.

	   // The target of the link is specified in the href field. This
	   // may be a relative URI or an absolute URI. If an absolute
	   // URI, it may be an NTIID or some other protocol (such as
	   // HTTP). Most commonly it will be simply an absolute path to
	   // be considered relative to the current server.

	   string href;
	   enum {
		   self, // The link is another way of reaching the containing entity
		   related, // The target is related to the containing entity
		   enclosure, // The target is potentially large data logically contained within this entity
		   alternate,
		   parent,
		   edit, //The href to use to make changes to this object
	   } rel;  //Relationship, represented as a string. This is only a  partial enumeration


	   optional string type; // The MIME type of the target.
	   optional string title; // The human-readable name of the target.
	   optional string ntiid; // The NTIID of the target
   }

   // TODO: Many of the object properties can be remodeled as
   // link relationships. Examples include following, Communities,
   // a Theadable's references, etc.


   struct Object {
	   optional readonly string Creator;
	   optional readonly time_t LastModified;
	   optional readonly time_t CreatedTime;
	   readonly string Class; // deprecated
	   readonly string MimeType;

	   // Any object may optionally have links to other
	   // objects, expressing a relationship between them.
	   // TODO: should this be inline on the object or part
	   // of external metadata? That gets to: do we need a
	   // 'entry' wrapper object?
	   readonly optional Link[] Links;
   }

   struct PersistentObject : Object {
	   // The OID is a persistent identifier for a given object. It will always
	   // refer to the same object. Its scope is across all users within a particular
	   // environment.
	   readonly oid_t OID;
   }

   mixin Contained {
	   string ContainerId;
   }


Users and Security
------------------

These objects describe users and things related to users.

.. code-block:: cpp

   struct Entity : PersistentObject {
	   readonly string Username; //The name is always in email format.
	   URL avatarUrl;
	   string realname;
	   string alias;
   }

   struct FriendsList : Entity<Contained> {
   	   //'friends' is a list of friends, possibly containing existing
   	   // users or other emails. When you POST/PUT an object, these
   	   // will be usernames (emails); the dataserver will resolve them
	   Entity friends[];
	   // A small set of URLs choosen to "uniquely" represent this
	   // list
	   URL CompositeGravatars[];
   }

   struct Person : Entity {
	   time_t lastLoginTime; //time_t format, you must set
	   out integer NotificationCount; //reset automatically when lastLoginTime is changed

	   string Presence; // "Online" or "Offline"

	   in string password; //Not echoed

	   //list of names of people we are not accepting
	   //shared data from
	   string ignoring[];
	   //List of names of people we agree to accept shared
	   //data from. Anytime someone adds us to a friends list,
	   //we start accepting data from them (unless we have
	   //previously ignored them). This generates a notification and
	   //stream event.
	   string accepting[];

	   //NOTE: ignoring and accepting can be posted to with a single
	   //string to add the user to the list (and ensure it's not in the counterpart list).
	   //They can also accept a dictionary with up to two keys, add and remove. The values for
	   //those keys are lists, and each element of that list will be added or removed
	   //as specified


	   //Communities I am a member of. I will see all data shared
	   //with the community if I follow the community. I will
	   //see data shared with people I follow if they share it with the
	   //community.
	   readonly string[] Communities;

	   //The names of individuals or communities I am following.
	   //I will see data these people share publically or
	   //to a community I belong to. When I add someone to a friends
	   //list, I automatically follow them.
	   string following[];

	   // These two fields (which are mutually exclusive) can be sent
	   // to mute (hide the conversation and all replies, including
	   // stream activity) or unmute a conversation. They take an
	   // NTIID OID. Notice that there is no provided list of all
	   // muted conversations: the use-case for unmuting is an "Undo"
	   // immediately following a mute, so the UI is expected to keep
	   // track of the last muted conversation.
	   in string mute_conversation;
	   in string unmute_conversation;

	   string email[]; //preferred order
	   //name is logon name is email
	   string organization;
	   string role[];
   }

   struct Preferences : Object {
	   //TODO
   }

UGD Content
-----------

These are definitions related to content that a user can generate.

.. note:: The type ``Anchored`` is defined in :doc:`content-anchoring`
   as a mixin including ``Contained.``



.. code-block:: cpp

   mixin Shareable {
	   Entity sharedWith[]; //Send as usernames (emails)
	   //TODO Flags
	   bool prohibitReSharing;
   }

   mixin Taggable {
       // Although the tag collections are defined as lists of words,
       // in reality they may be treated as unordered sets.
       // Spaces in individual terms may be split. Capitilazition may
       // not be preserved. These are plain text, and any HTML
       // will simply cause the term to be discarded


       // Tags that are added automatically, somehow derived from the data
       string[] AutoTags;
       // Tags that are added manually by the user.
       string[] tags;
   }

   //NOTE: Bookmarks do not currently exist
   struct Bookmark : PersistentObject<Anchored,Shareable,Taggable> { }

   // NOTE that it is possible to update only the sharing of a
   // highlight or note, by sending only the 'sharedWith' field and
   // leaving all other fields absent.

   //Created from a DOM Range indicating a user-selection.
   //NOTE: Does not currently exist as a creatable entity, only
   //an abstract concept.
   struct SelectedRange : Bookmark {
        string selectedText; //Populated from the Range object's string value: http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-range-stringifier
   }

   struct Highlight : SelectedRange {
        string style; //Variants of highlights. Currently, 'plain' required
   }

   struct Redaction : SelectedRange {
        optional string replacementContent;
        optional string redactionExplanation;
   }

   mixin Threadable {
	   oid_t inReplyTo;
	   oid_t references[];
   }

   struct Note : Highlight <Threadable, Anchored, Shareable> {
	   //An ordered list of objects (strings or objects) that make up the body.
	   //In particular, Canvas objects can appear here as can HTML strings.
	   Object[] body;
   }

.. note:: For a more full explanation of a Redaction object, see
   :py:class:`nti.dataserver.interfaces.IRedaction`

Activity Stream
---------------

.. code-block:: cpp

   struct Change : Object<Contained> {
	   enum {
		   CREATED,
		   MODIFIED,
		   CIRCLED
	   } changeType;
	   Object object;
   }

   struct ActivityStream : Object<Contained> {
	   Change changes[];
	   //TODO: If we support older/multiple ranges,
	   //some indication here of which part of range,
	   //whether there is more?
   }
