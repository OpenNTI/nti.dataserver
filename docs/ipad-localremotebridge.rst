==========================================
IPad Local Remote User Data Storage Bridge
==========================================

This document describes the current implementation details of user
generated data (UGD) persistence for the ipad application.  An outline of
the current storage implementations is provided with an emphasis on
how they are bridged to provide seamless online/offline interaction.

Introduction
============

To support a seamless experience when working with UGD objects
regardless of whether a dataserver connection is available to the
ipad, the application makes use of both local and remote storage.  The interaction
of this local and remote storage is managed by a storage bridge.  The
storage bridge is responsible for determining when and where a
particular piece of user data is updated as well as how and when any
necessary syncing is performed. The guiding principal in both the design
and development of the storage bridge is **The server is always right**.  The remainder
of this document describes implementation details for the current iteration of UGD storage
in the ipad application.

UGD Storage
===========


Storage Operations
------------------

Operations on user data storage can be classified into two main types.

**Read Operations**
	Operations that read a users friends lists
	or retrieves user generated data for a given NTIID.

**Write Operations**
	Operations that modify user storage.  For example, creating a whiteboard, deleting a highlight,
	or editing a note.

In addition storage implementations can optionally implement a message
that will be called when NTIChanges are processed from the socket.
This is useful for providing the appearance of *live* content updating
and could be used to initiate a remote refresh or simply load the item
from the change into storage.  If storage does not support this
optional message it will not be notified of incoming changes and will
need to do its own polling for updates.

Write Operations
________________

The currently supported write operations are:

- Persist object
- Delete object
- Update sharing of object
- Save friends list
- Update friends list

The first two are general operations for the creation/modification and
deletion of userdata.  The latter three are special cases
of \"Persist object\" provided so specific storage implementations can take advantage of optimizations supported by the dataserver.
Specific storage implementations may choose to use these optimizations
or simply implement the final 3 operations by calling \"Persist
Object".

Read Operations
_______________

The currently supported read operations are:

- Load data for container
- Load friends lists

\"Load data for container\" is, as it sounds, used to query storage
for all the UGD associated with a particular container (NTIID).  The
result of this operation is the collection UGD visible to the user as
well as any changes that have been associated to the given container
or it's child containers recusrivesly (UserGeneratedDataAndRecursiveStream).
Similarly \"Load friends lists\" is used to query storage for the
friends lists associated with the storage's owner.


Remote Storage
--------------

Remote storage provides an interface to a remote NTI dataserver.
By definition remote storage requires external resources and therefore
an external network condition. The current remote storage
implementation is based on HTTP CRUD operations.  In
fact it is simple wrapper around the old HTTP persistence objects.

In addition to providing the base storage operations described above,
remote storage implementations provide an indication of whether or not
they think their remote counterpart (e.g. nti dataserver) is
unreachable.  This allows for remote storage owners (like the storage
bridge) to omit calls to remote storage that they know will not succeed.

Local Storage
-------------

Local storage provides an interface for local storage of UGD.  Some
examples of resources that could be used to back local storage are core dats, sqlite db, or
plain file system access. Local storage **must** be accessible without
access to any outside resources.  This is important to ensure the ipad
application can function with or without a dataserver connection
whenever possible.

Local storage implementations may choose to back local storage using
any method they see fit provided it functions without
external resources.  In addition, for synching/merging purposes local
storage must be able to distinguish between objects that have been
deleted locally and those that do not exist locally.  Because of this
it is useful for local storage to implement the \"Delete object\"
operation as \"Mark as deleted\".

In addition to providing the base storage operations described above,
local storage implementations must also provide several methods for
syncing/merging when working in a local/remote bridged storage
environment. These messages include:

- Reset last modified for container
- Replace object in local storage with object from remote
- Remove object from local storage
- Fetch objects to sync for container
- Fetch containers that may need syncing
- Merge UGD and Stream data into container
- Merge UGD into container
- Fetch last modified for container
- Lock container
- Release container lock
- Obtain lock on container

The first three messages are employed by the bridge to update local storage
with the result of a write operations performed on remote storage.
See \"Storage Bridge\" for details.

The remaining additional messages are used by the bridge to keep local
and remote stores in sync.  See \"Storage Bridge\" and \"Container
Locking\" for more details.

Container Locking
-----------------

Because access to local storage can occur on different threads when
used in a bridged environment local storage must provide some basic
locking on containers.  The exact details of how local storage tracks
locking information is an implementation detail but it must provide
the ability to unconditionally lock and release containers as well as
provide conditional locking for containers before a block is run.


Storage Bridge
==============

As discussed above the Storage Bridge's responsibility is two fold.
It is then component in charge of coordinating read and write storage operations between
local and remote storage, and implementing any logic necessary for
keeping the two storage implementations in sync.  Storage Bridge
implemenations implement the 7 (5 write, 2 read) storage operations
outlined in \"Storage Operations\" and can therefore be dropped in
any place user data storage is required.

Storage Cordinations
--------------------

When a Storage Bridge is asked to perform one of the read or write
storage operations it must decide how to utilize its local and remote
storage implementations to fulfill the request.  Our bridge
implementation makes a distinction between read and write operations.

For read operations our storage bridge always returns data that has
been read from local storage.  To ensure the most up to date data is
returned when requested the storage bridge will first execute a
remote to local sync (See next section for details) of the container
being requested.  When the sync is complete the containers data will
be read from local storage and returned to the caller.

For write operations our storage implemenation makes a distinction
between those operations affecting user data objects (notes,
highlights, canvas, etc.) and friendslist.  Friendslist creation and
modification has a heavy relience on the server for things like user
search.  For this reason it seems unreasonable to expect friendslist
creation and modification to work seemlessly offline.  Because of this
the decision was made to simply pass these operations directly through
to remote storage.  Although performing these operations while
the pad is offline should fail gracefully, it is expected that the UI
will coordinate with remote storage on this implementation detail to
disable the creation/modification of friends lists.

The remaining write operations are coordinated between local and
remote storage.  The bridge first performs the operation on local
storage.  Currently if the local storage operation fails the entire
storage operation fails and the failure callback is called.  It's
questionable as to whether or not this is the correct behaviour. With
some more work around synching it is possible that we could perform
the operation on remote storage and then attempt to store remote
storage operation's result locally.  This was initially deemed unnecessary but we could
revist this decision if we deem it beneficial.  If the local storage
operation is succesfull the operation is then performed on remote
storage.  The operation on remote storage can end in one of three
ways.  The result of the operation can be succesfull, can not complete
becuase remote storage is unavailable, or can not complete because of
an error in remote storage (dataserver issue).  If the remote
operation is successfull the local object is replaced with the remote
result so that any dataserver expanded fields exist in remote storage,
and the callback is called with the remote result.  If the remote
operation cannot be completed because remote storage is unavailable
the callback is called with the result of the local operations.  It is
expected that at some point in the future, possible as late as the
next time the application is started, this local only object will be
synced to remote storage. Lastly, if the remote storage operation
fails because of an error in remote storage, the object is removed
from local storage, and the last modified for the local container is reset
so a remote to local sync (see next section) will occur at the next
possible time.

In addition to performing remote to local syncing as part of read
operations the bridge may perform synching as a result of exeternal
events.  Our current implementation will perform a sync for any
containers that have outstanding objects every 10 minutes while the
app is running in the foreground.

Remote to Local Synching
------------------------

The bridge uses a remote to local synching procedure to keep local
storage in sync with remote storage.  When a sync is requested for a
given container it will be performed if there is not already a sync
for that container in progress.  If there is an in progress sync the
callback will be held and called back when the in progress sync
finishes. When a sync is performed for a
given container the following procedure takes place.  If remote storage is unavailable the
sync completes immediately.  If remote storage is available the last
modified for the container is read from local storage and remote data
is requested using the if-modified-since header with that last
modified time.  If user data is returned it is merged into local
storage (see next section).  Lastly any local objects that need to be
pushed to remote storage are pushed up.  Objects that need to be
created or updated remotely are done so using the remote storage's
write operations and on completion the local object is replaced with
the result of the remote call.  For objects that need to be deleted
remotely the object is deleted and on success it is removed from local
storage.  Any object being synced to remote storage that fails is
removed from local storage.  When all local to remote operations have
been completed the completion callback will be called.

Merging Remote Objects into Local Storage
_________________________________________

To merge a set of remote objects returned from remote storage as part
of a remote to local sync operation the following procedure is
applied.  Each remote object that doesn't exist in local storage is
added to local storage.  Objects in local storage that are
not in the set of remote objects are deleted from local storage if
they are not an outstanding edit or creation.  Objects that exist in
both local storage and the set of remote objects are handled as
follows. If the last modified time for the remote object is newer than
the last modified time for the local object, the local object is
replaced with the remote object.  If the local object's last modified time is
newer than the remote object's it should be an outstanding change that
needs to be synced and we assert as such.

Locking
-------

Because read/write operations and remote to local synching can be
triggered from from multiple threads (user interaction on the main
thread, sync due to container load because of reachability, sync due
to the sync timer firing, etc.) the storage bridge works in
conjunction with the local storage implementation to provide container
locking via a lock count.  A containers lock count is unconditionally
incremented and decremented before and after write operations
respectively. Before a sync can occur for a container the bridge must be able to
obtain a lock on the requested container (lock count is zero and then
gets incremented).
