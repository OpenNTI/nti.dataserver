=====================
 User Management
=====================

Scripts
=========================

Command Line
------------

These command line scripts can perform a variety of user administration functions.

Accounts can also be created on the command line:

.. command-output:: nti_create_user -h

Add or remove friends:

.. command-output:: nti_add_remove_friends -h

Create friends list:

.. command-output:: nti_create_friendslist -h

Export entities:

.. command-output:: nti_export_entities -h

Follow an entity:

.. command-output:: nti_follow_entity -h

Delete a user:

.. warning:: It is critically important that you supply the ``site``
			 argument for the user's home site. Failure to do so can
			 result in corruption.

.. command-output:: nti_remove_user -h

Set a password:

.. command-output:: nti_set_password -h

Set a user attribute:

.. command-output:: nti_set_user_attribute -h
