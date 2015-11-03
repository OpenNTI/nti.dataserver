==========
 Flagging
==========

This document talks about how flagging and moderation are
implemented. It is very similar to :doc:`liking`.

Model
=====

The implementation of the API and storage lives in the
``nti.dataserver.flagging`` module. It implements a simple
global utility for tracking flagged objects.

.. automodule:: nti.dataserver.flagging
	:members:
	:private-members:


Views
=====

The ability to flag and moderate is exposed as a set
of links on objects connected to views defined in the
``nti.appserver.flagging_views`` package.

.. automodule:: nti.appserver.flagging_views
	:members:
	:private-members:


	.. data:: FLAG_VIEW

		The name of the view used for flagging: `flag`

	.. data:: FLAG_AGAIN_VIEW

		The name of the view used for flagging again: `flag.metoo`

	.. data:: UNFLAG_VIEW

		The name of the view used to clear the flagged status of something: `unflag`


Utils
-----

.. automodule:: nti.appserver._util
