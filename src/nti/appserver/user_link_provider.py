#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Persistent implementation of :class:`nti.appserver.IAuthenticatedUserLinkProvider`.
In general, links will be added to the object provided by this class. They will be expected
to provide a named view on the user that can be used to GET information, and when the action is complete,
a DELETE to that same view will remove the link (if it is not removed implicitly by some other action; this
could be done with one of the workflow packages like ``hurry.workflow`` but for now our needs are simple
enough that they are overkill.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from zope.annotation.interfaces import IAnnotations

from BTrees.OOBTree import OOTreeSet
from nti.utils import sets

from nti.dataserver import interfaces as nti_interfaces
from nti.appserver import interfaces as app_interfaces
from pyramid import interfaces as pyramid_interfaces

from nti.dataserver.links import Link
from nti.dataserver import authorization as nauth

from pyramid.view import view_defaults
from nti.appserver import httpexceptions as hexc
from ._util import link_belongs_to_user

# We store links in an OOTreeSet annotation on the User object
_LINK_ANNOTATION_KEY = __name__ + '.LinkAnnotation'

def add_link( user, link_name ):
	"""
	Add the given link name to the user.

	:param user: An annotatable user.
	:param unicode link_name: The link name.
	"""

	the_set = IAnnotations( user ).get( _LINK_ANNOTATION_KEY )
	if the_set is None:
		the_set = OOTreeSet()
		IAnnotations( user )[_LINK_ANNOTATION_KEY] = the_set
	the_set.add( link_name )

def has_link( user, link_name ):
	"""
	Primarily for testing, answer whether the user is known to
	have the given link.

	:param user: An annotatable user.
	:param unicode link_name: The link name.
	"""

	the_set = IAnnotations( user ).get( _LINK_ANNOTATION_KEY, () )
	return link_name in the_set


def delete_link( user, link_name ):
	"""
	Ensure the given user does not have a link with the
	given name.

	:param user: An annotatable user.
	:param unicode link_name: The link name.
	:return: A truthy value that will be true if the link
		existed and was discarded or false of the link didn't exist.
	"""

	the_set = IAnnotations( user ).get( _LINK_ANNOTATION_KEY )
	if the_set is None:
		return

	return sets.discard_p( the_set, link_name )

@interface.implementer(app_interfaces.IAuthenticatedUserLinkProvider)
@component.adapter(nti_interfaces.IUser,pyramid_interfaces.IRequest)
class PersistentUserLinkProvider(object):

	def __init__( self, user, request=None ):
		self.user = user

	def get_links( self ):
		the_set = IAnnotations( self.user ).get( _LINK_ANNOTATION_KEY, () )
		result = []
		for link_name in the_set:
			link = Link( self.user, rel=link_name, elements=("@@" + link_name,))
			link_belongs_to_user( link, self.user )
			result.append( link )
		return result

@view_defaults(
			   route_name='objects.generic.traversal',
			   request_method='DELETE',
			   permission=nauth.ACT_DELETE,
			   context=nti_interfaces.IUser )
class AbstractUserLinkDeleteView(object):
	"""
	Subclass this object to get DELETE behaviour for user links.
	All you have to do is supply the link name in a class attribute,
	and decorate the __call__ method with the view name.
	"""

	LINK_NAME = None

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		if delete_link( self.request.context, self.LINK_NAME ):
			return hexc.HTTPNoContent() # 204
		return hexc.HTTPNotFound() # 404
