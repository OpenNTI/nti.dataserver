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
from nti.externalization import interfaces as ext_interfaces

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(interfaces.ILikeable)
class LikeDecorator(object):

	def __init__( self, ctx ): pass

	def decorateExternalMapping( self, context, mapping ):
		like_count = 0
		rating = _lookup_like_rating_for_read( context )
		if rating:
			like_count = rating.numberOfRatings

		mapping['LikeCount'] = like_count

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

# We define likes simply as a rating of 1, and unlikes remove
# the user from the list

def like_object( context, username ):
	"""
	Like the `context` idempotently.
	:param context: An class:`nti_interfaces.ILikeable` object.
	:param username: The name of the user liking the object. Should not be
		empty.
	:return: An object with a boolean value; if action was taken, the value is True-y.
	:raises TypeError: If the `context` is not really likeable.
	"""

	rating = _lookup_like_rating_for_write( context )
	if rating.userRating( username ) is None:
		rating.rate( 1, username )
		return rating

def unlike_object( context, username ):
	"""
	Unlike the `object`, idempotently.
	:param context: An class:`nti_interfaces.ILikeable` object.
	:param username: The name of the user liking the object. Should not be
		empty.
	:return: An object with a boolean value; if action was taken, the value is True-y.
	:raises TypeError: If the `context` is not really likeable.
	"""

	rating = _lookup_like_rating_for_read( context )
	if rating and rating.userRating( username ) is not None:
		rating.remove_rating( username )
		return rating

def likes_object( context, username ):
	"""
	Determine if the `username` likes the `context`.
	:param context: An class:`nti_interfaces.ILikeable` object.
	:param username: The name of the user liking the object. Should not be
		empty.
	:return: An object with a boolean value; if the user likes the object, the value is True-y.
	"""
	rating = _lookup_like_rating_for_read( context )
	if rating and rating.userRating( username ) is not None:
		return rating
