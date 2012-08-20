===============
 Logon Process
===============

Account Creation
================

ReST
----

Accounts can be created through the ReST interface.

.. automodule:: nti.appserver.account_creation_views
	:private-members:

Command Line
------------

Accounts can also be created on the command line:

.. command-output:: nti_create_user -h

Logon APIs
==========

.. automodule:: nti.appserver.logon
	:private-members:

Request Authentication
======================

.. automodule:: nti.appserver.pyramid_auth
	:private-members:

Database Sharding
=================
.. This isn't really the right place for this

.. automodule:: nti.dataserver.shards
	:private-members:
