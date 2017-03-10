#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other functions related to forums and blogs.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import lifecycleevent

from zope.event import notify

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.appserver.ugd_edit_views import UGDDeleteView

from Acquisition import aq_base

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

from nti.dataserver.contenttypes.forums.interfaces import ICommentPost
from nti.dataserver.contenttypes.forums.interfaces import IGeneralForum
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntry
from nti.dataserver.contenttypes.forums.interfaces import IGeneralHeadlineTopic

_view_defaults = dict(route_name='objects.generic.traversal',
					  renderer='rest')
_c_view_defaults = _view_defaults.copy()
_c_view_defaults.update(permission=nauth.ACT_CREATE,
						request_method='POST')
_r_view_defaults = _view_defaults.copy()
_r_view_defaults.update(permission=nauth.ACT_READ,
						request_method='GET')
_d_view_defaults = _view_defaults.copy()
_d_view_defaults.update(permission=nauth.ACT_DELETE,
						request_method='DELETE')

def _do_aq_delete(theObject):
	"""
	Delete an object from its parent container, noting
	that the object's dict may not have
	the correct (unwrapped) __parent__ due to errors
	in previous versions. We should really do a migration.

	(The BTree container loads the object from its internal
	data by name, bypassing our higher level that would aq wrap
	them. Since events are only fired if cont[key].__parent__ = cont,
	aq wrappers in the dict screw us up).
	"""

	base_parent = aq_base(theObject.__parent__)
	theObject.__dict__['__parent__'] = base_parent
	del base_parent[theObject.__name__]

@view_config(context=IPersonalBlogEntry)
@view_config(context=IGeneralHeadlineTopic)
@view_defaults(**_d_view_defaults)
class HeadlineTopicDeleteView(UGDDeleteView):
	"""
	Deleting an existing topic
	"""

	# # Deleting an IPersonalBlogEntry winds up in users.users.py:user_willRemoveIntIdForContainedObject,
	# # thus posting the usual activitystream DELETE notifications

	def _do_delete_object(self, theObject):
		# Delete from enclosing container
		_do_aq_delete(theObject)
		return theObject

@view_config(context=IGeneralForum)
@view_defaults(**_d_view_defaults)
class ForumDeleteView(UGDDeleteView):
	"""
	Deleting an existing forum
	"""

	def _do_delete_object(self, theObject):
		# Standard delete from enclosing container. This
		# dispatches to all the sublocations and thus removes
		# the comments, etc, and into the activity streams
		_do_aq_delete(theObject)
		return theObject

@view_config(context=ICommentPost)
@view_defaults(**_d_view_defaults)
class CommentDeleteView(UGDDeleteView):
	"""
	Deleting an existing forum comment.

	This is somewhat unusual as we leave an object behind to mark
	the object as deleted (in fact, we leave the original object
	behind to preserve its timestamps and IDs) we only apply a marker and
	clear the body.
	"""

	def _do_delete_object(self, theObject):
		deleting = aq_base(theObject)
		interface.alsoProvides(deleting, IDeletedObjectPlaceholder)

		# TODO: Events need to fire to unindex, once we figure
		# out what those are?
		# We are I18N as externalization time
		deleting.title = None
		deleting.body = None
		deleting.tags = ()
		# Because we are not actually removing it, no IObjectRemoved events fire
		# but we do want to sent a modified event to be sure that timestamps, etc,
		# get updated. This also triggers removing from the user's Activity
		notify(lifecycleevent.ObjectModifiedEvent(deleting))
		return theObject

del _view_defaults
del _c_view_defaults
del _r_view_defaults
del _d_view_defaults
