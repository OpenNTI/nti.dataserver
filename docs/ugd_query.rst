==============================
 Querying User Generated Data
==============================

This document discusses how user generated data is queried.

Views
=====

As mentioned in :doc:`content-resolving`, there are a number of
different collections of user generated data and ways to access them,
including directly (``UserGeneratedData``) and recursively
(``RecursiveUserGeneratedData``), only including "notable" items
(``RUGDByOthersThatIMightBeInterestedIn`` --- only defined for the
root NTIID) a view of incoming changes only (``Stream``) and incomnig
changes recursively (``RecursiveStream``), plus some optimized
combinations of the two (``RecursiveUGDAndStreamView``).

A special view for showing "activity" of a user, which includes
content-related UGD plus other activity (such as forum/blog activity)
is found in the
:class:`nti.appserver.user_activity_views.UserActivityGetView`, which
is located via means of a special link relationship.

Security
--------

When the user in the URL is the same as the authenticated user, all
data created by and shared with that user is available. When they are
different, only data created by the target user is visible to the
authenticated user, and only when the two users share a Community
relationship.

Query Parameters
----------------

The parameters that can be used to control the results are documented
on the
method that handles them, :meth:`~nti.appserver.ugd_query_views._UGDView._sort_filter_batch_result`.


UGD View Implementation
=======================

The view code that implements these queries is defined in the ``nti.appserver.ugd_query_views`` module.

.. automodule:: nti.appserver.ugd_query_views
	:members:
	:private-members:


Activity View Implementation
============================

The activity view code extends the general UGD view code and is found
in the ``nti.appserver.user_activity_views`` module.

.. automodule:: nti.appserver.user_activity_views
	:members:
