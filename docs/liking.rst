===============================
 Liking, Rating and Favoriting
===============================

This document talks about how liking and its related activities are
implemented.

Model
=====

The implementation of the API and storage lives in the
``nti.dataserver.liking`` module. It is currently based on the
:mod:`contentratings` package.

.. automodule:: nti.dataserver.liking
	:members:
	:private-members:

	.. data:: LIKE_CAT_NAME

	Category name for 'liking'


	.. data:: FAVR_CAT_NAME

	Category name for 'favorites'

Views
=====

The ability to like/unlike and favorite/unfavorite is exposed as a set
of links on objects connected to views defined in the
``nti.appserver.liking_views`` package.

.. automodule:: nti.appserver.liking_views
	:members:
	:private-members:


Contentratings
==============

.. automodule:: contentratings

Contentratings interfaces
-------------------------

.. automodule:: contentratings.interfaces

Contentratings Storage
----------------------

.. automodule:: contentratings.storage
