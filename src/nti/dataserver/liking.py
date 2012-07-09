#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
An implementation of liking and liking adapters.

The primary implementation here is built on the :mod:`contentratings`
package, but takes care to not create persistent objects
for read-only requests (e.g., viewing the likes of an object). [TODO: An alternate
approach is to create these objects when the object is created by adapting it
directly.]

$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope import component
from zope.annotation import interfaces as an_interfaces

import contentratings.interfaces
from contentratings.category import BASE_KEY
from contentratings.storage import UserRatingStorage

from . import interfaces
from . import links
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization import interfaces as ext_interfaces

from pyramid.security import authenticated_userid
from pyramid.threadlocal import get_current_request

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(interfaces.ILikeable)
class LikeDecorator(object):

	def __init__( self, ctx ): pass

	def decorateExternalMapping( self, context, mapping ):
		like_count = 0
		i_like = False
		rating = _lookup_like_rating_for_read( context )
		if rating:

			like_count = rating.numberOfRatings
			# TODO: The 'unlike' and 'like' links
			# TODO: What's the best way to get this info? The
			# rating object has a userid, but to make that work we have to
			# subclass
			uid = authenticated_userid( get_current_request() )
			i_like = rating.userRating( uid ) if uid else False

		mapping['LikeCount'] = like_count
		link = links.Link( context, rel=('unlike' if i_like else 'like') )
		_links = mapping.setdefault( StandardExternalFields.LINKS, [] )
		_links.append( link )


CAT_NAME = 'likes'

def _lookup_like_rating_for_read( context ):
	"""
	:param context: Something that is :class:`interfaces.ILikeable`
		and, for now, can be adapted to an :class:`contentratings.IUserRating`
		with the name of 'like'.
	:return: A user rating object, if one already exists. Otherwise None.
	"""

	# While we're using the default storage objects, as soon as they
	# are created the annotations are set, which can lead to too many conflicts.
	# we thus try to defer that.
	# This is a duplication of code from contentratings.cagetory

	# Get the key from the storage, or use a default
	key = getattr(UserRatingStorage, 'annotation_key', BASE_KEY)
	# Append the category name to the dotted annotation key name
	key = str(key + '.' + CAT_NAME)
	# Retrieve the storage from the annotation, or create a new one
	annotations = an_interfaces.IAnnotations(context)
	storage = annotations.get( key )

	if storage:
		# Ok, we already have one. Use it.
		return _lookup_like_rating_for_write( context )

def _lookup_like_rating_for_write( context ):
	return component.getAdapter( context, contentratings.interfaces.IUserRating, name=CAT_NAME )
