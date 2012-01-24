==========================================
IPad Local Remote User Data Storage Bridge
==========================================

This document describes the current implementation details of user
generated data (UGD) persistence for the ipad application.  An outline of
the current storage implementations is provided with an emphasis on
how they are bridge to provide seamless online/offline interaction.

Introduction
============

To support a seamless experience when working with UGD objects
regardless of whether a dataserver connection is available to the
ipad, the application makes use of both local and remote storage.  The interaction
of this local and remote storage is managed by a storage bridge.  The
storage bridge is responsible for determining when and where a
particular piece of user data is updated as well as how and when any
necessary local to remote syncing is performed. The guiding principal in both the design
and development of the storage bridge is **The server is always right**.  The remainder
of this document describes the implementation details for the current iteration of UGD storage
in the ipad application.

UGD Storage
===========


Storage Operations
------------------

Operations on user data storage can be classified into two main types.

**Read Operations**
	Operations that read dching a users friends lists
	or retrieving user generated data for a given NTIID.

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

The first two are general operations for the creation/modification and deletion of userdata.  The latter three are really just special cases
of \"Persist object\" provided so specific storage implementations can take advantage of optimizations supported by the dataserver.
Specific storage implementations may choose to use these optimizations
or simply implement the final 3 operations by calling \"Persist
Object". The next section outlines the UGD storage bridge implementation details
for the aforementioned \"Write Operations\".

Read Operations
_______________

The currently supported read operations are:

- Load data for container
- Load friends lists

\"Load data for container\" is, as it sounds, used to query storage
for all the UGD associated with a particular container (NTIID).  The
result of this operation is the collection UGD visible to the user as
well as any changes that have been associated to the given container.
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
they know their remote counterpart (e.g. nti dataserver) is
unreachable.  This allows for remote storage owners (like the storage
bridge) to omit calls to local storage that they know will not succeed.

Local Storage
-------------

Local storage provides an interface to local storage of UGD.  Some
examples of resources that could be used to back local storage are a core data store, sqlite db, or
plain file system access. Local storage **must** be accessible without
access to any outside resources.  This is important to ensure the ipad
application can function with or without a dataserver connection
whenever possible.

Local storage implementations may choose to back local storage using
any method they see fit provided it functions without
external resources.  In addition for synching/merging purposes local
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
+++++++++++++++++

Because access to local storage can occur on different threads when
used in a bridged environment local storage must provide some basic
locking on containers.  The exact details of how local storage tracks
locking information is an implementation detail but it must provide
the


Storage Bridge
==============

