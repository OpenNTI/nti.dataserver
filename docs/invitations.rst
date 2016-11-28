=============
 Invitations
=============

This document talks about how invitation codes are implemented.

Model
=====

The implementation of the API and storage lives in the
``nti.invitations`` package.

.. automodule:: nti.invitations

.. automodule:: nti.invitations.interfaces

.. automodule:: nti.invitations.utils


Views
=====

The implementation of the external interface for invitations lives
in the ``nti.app.invitations.views`` module.

.. note:: This functionality is currently very minimal, growing on
   demand. Notice that the model is significantly more featureful than
   what we are exposing here, which is just based on codes. Expect
   eventually that there will be a public ``Invitation`` object that
   users will be able to edit attributes of (such as description text,
   permissible usernames/emails, etc) or email out. There might also
   be an folder/collection allowing listing/sorting/searching all
   invitations a user has created, and possibly one for any
   outstanding invitations that might be joinable.

Accepting
---------

Besides being acceptable during account creation (see :func:`nti.appserver.account_creation_views.account_create_view`),
views are provided on a User to accept invitations. The User will have
the :const:`nti.app.invitations.views.REL_ACCEPT_INVITATIONS`
link type for this purpose.

Creating
--------

As mentioned above, the use of invitations is currently minimal, and
limited to extending an invitation to join an
:class:`nti.dataserver.users.friends_lists.DynamicFriendsList`. To its
creator, such an object will have a
:const:`nti.app.invitations.views.REL_TRIVIAL_DEFAULT_INVITATION_CODE`
link type that can be used to fetch the invitation code (creating the
invitation on demand).


.. automodule:: nti.app.invitations.views
	:members:
	:private-members:
