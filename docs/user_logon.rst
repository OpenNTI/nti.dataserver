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

.. autoclass:: nti.appserver.site_policies.RequestAwareUserPlacer

Command Line
------------

Accounts can also be created on the command line:

.. command-output:: nti_create_user -h

Bounced Emails
==============

If we detect that the user has entered invalid email addresses,
we go into the bounce-recovery states and action must be taken
by the user through the ReST interface.

.. automodule:: nti.appserver.bounced_email_workflow

Batch Process
-------------

Detecting that email addresses are invalid is done with a batch
process:

.. command-output:: nti_bounced_email_batch -h

Account Recovery
================

Account recovery actions for forgotten usernames and passwords can
be initiated through the ReST interface.

.. automodule:: nti.appserver.account_recovery_views
	:private-members:


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

Command Line
------------

Once the database is in place, and configured, the dataserver has to
be made aware of the database and told to use it as a shard:

.. command-output:: nti_init_shard -h
