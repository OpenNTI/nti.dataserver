=============
 Invitations
=============

This document talks about how invitation codes are implemented.

Model
=====

The implementation of the API and storage lives in the
``nti.appserver.invitations`` package.

.. automodule:: nti.appserver.invitations

.. automodule:: nti.appserver.invitations.interfaces

.. automodule:: nti.appserver.invitations.utility


Views
=====

Besides being acceptable during account creation (see :func:`nti.appserver.account_creation_views.account_create_view`),
views are provided on a user to accept invitations.

.. automodule:: nti.appserver.invitation_views
	:members:
	:private-members:
