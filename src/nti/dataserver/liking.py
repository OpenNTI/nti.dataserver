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

LIKE_CAT_NAME = 'likes'
FAVR_CAT_NAME = 'favorites'

def _lookup_like_rating_for_read( context, cat_name=LIKE_CAT_NAME ):
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
	key = str(key + '.' + cat_name)
	# Retrieve the storage from the annotation, or create a new one
	annotations = an_interfaces.IAnnotations(context)
	storage = annotations.get( key )

	if storage:
		# Ok, we already have one. Use it.
		return _lookup_like_rating_for_write( context, cat_name=cat_name )

def _lookup_like_rating_for_write( context, cat_name=LIKE_CAT_NAME ):
	return component.getAdapter( context, contentratings.interfaces.IUserRating, name=cat_name )

# We define likes simply as a rating of 1, and unlikes remove
# the user from the list.
# Favorites, aka Bookmarks, are implemented the same way. This has the advantage
# of keeping it all object-local; the disadvantage that an index is required to
# have the user query for his favorites (such an index can be maintained
# by listening for the ObjectRatedEvents sent by a RatingCategory; NOTE: this
# only seems to fire when ratings are added, not when ratings are removed so it's not
# quite sufficient to maintain an index).

def _rate_object( context, username, cat_name ):

	rating = _lookup_like_rating_for_write( context, cat_name )
	if rating.userRating( username ) is None:
		rating.rate( 1, username )
		return rating

def _unrate_object( context, username, cat_name ):

	rating = _lookup_like_rating_for_read( context, cat_name )
	if rating and rating.userRating( username ) is not None:
		rating.remove_rating( username )
		return rating

def _rates_object( context, username, cat_name ):
	rating = _lookup_like_rating_for_read( context, cat_name )
	if rating and rating.userRating( username ) is not None:
		return rating


def like_object( context, username ):
	"""
	Like the `context` idempotently.
	:param context: An class:`nti_interfaces.ILikeable` object.
	:param username: The name of the user liking the object. Should not be
		empty.
	:return: An object with a boolean value; if action was taken, the value is True-y.
	:raises TypeError: If the `context` is not really likeable.
	"""
	return _rate_object( context, username, LIKE_CAT_NAME )


def unlike_object( context, username ):
	"""
	Unlike the `object`, idempotently.
	:param context: An class:`nti_interfaces.ILikeable` object.
	:param username: The name of the user liking the object. Should not be
		empty.
	:return: An object with a boolean value; if action was taken, the value is True-y.
	:raises TypeError: If the `context` is not really likeable.
	"""
	return _unrate_object( context, username, LIKE_CAT_NAME )


def likes_object( context, username ):
	"""
	Determine if the `username` likes the `context`.
	:param context: An class:`nti_interfaces.ILikeable` object.
	:param username: The name of the user liking the object. Should not be
		empty.
	:return: An object with a boolean value; if the user likes the object, the value is True-y.
	"""
	return _rates_object( context, username, LIKE_CAT_NAME )


def favorite_object( context, username ):
	"""
	Favorite the `context` idempotently.
	:param context: An class:`nti_interfaces.IFavoritable` object.
	:param username: The name of the user favoriting the object. Should not be
		empty.
	:return: An object with a boolean value; if action was taken, the value is True-y.
	:raises TypeError: If the `context` is not really likeable.
	"""
	return _rate_object( context, username, FAVR_CAT_NAME )


def unfavorite_object( context, username ):
	"""
	Unfavorite the `object`, idempotently.
	:param context: An class:`nti_interfaces.IFavoritable` object.
	:param username: The name of the user unfavoriting the object. Should not be
		empty.
	:return: An object with a boolean value; if action was taken, the value is True-y.
	:raises TypeError: If the `context` is not really likeable.
	"""
	return _unrate_object( context, username, FAVR_CAT_NAME )


def favorites_object( context, username ):
	"""
	Determine if the `username` has favorited the `context`.
	:param context: An class:`nti_interfaces.IFavoritable` object.
	:param username: The name of the user possibly favoriting the object. Should not be
		empty.
	:return: An object with a boolean value; if the user likes the object, the value is True-y.
	"""
	return _rates_object( context, username, FAVR_CAT_NAME )



from zope.app.container.contained import Contained
from persistent import Persistent
import BTrees
from BTrees.Length import Length
from contentratings.rating import Rating


@interface.implementer(contentratings.interfaces.IUserRating,contentratings.interfaces.IRatingStorage)
class _BinaryUserRatings(Contained, Persistent):
	"""
	BTree-based storage for binary user ratings, where a user can either have rated
	(with a 1) or not; no other value is permitted. Furthermore, the anonymous
	user is prohibited. This allows for optimizations in
	storage and implementation.

	Compare with :class:`contentratings.storage.UserRatingStorage` for a full implementation.
	"""

	scale = 1

	def __init__(self):
		super(_BinaryUserRatings,self).__init__()
		# Since we are simply recording the presence or absence of a user,
		# can can use a simple set
		self._ratings = BTrees.family64.OO.TreeSet()
		self._length = Length()


	def rate(self, rating, username=None, session_key=None):
		"""Set a rating for a particular user"""
		if rating != 1 or not username or session_key: # pragma: no cover
			__traceback_info__ = rating, username, session_key
			raise ValueError( "Rating must be 1, only username must be given" )

		if username not in self._ratings:
			self._ratings.add( username )
			self._length.change(1)

		return Rating( 1, username )

	def userRating(self, username=None):
		"""Retreive the rating for the specified user, which must be provided."""
		if not username: raise ValueError( "Must give username" ) #pragma: no cover
		if username in self._ratings:
			return Rating( 1, username )

	def remove_rating(self, username):
		"""Remove the rating for a given user"""
		self._ratings.remove(username)
		self._length.change(-1)
		return Rating( 1, username )

	def all_user_ratings(self, include_anon=False):
		"""
		:param bool include_anon: Ignored.
		"""
		return (Rating( 1, username) for username in self.all_raters)

	@property
	def all_raters(self):
		return self._ratings.keys()

	@property
	def numberOfRatings(self):
		return self._length()

	@property
	def averageRating(self):
		return 1 if self._length() else 0

	def last_anon_rating(self, session_key):
		"""Returns a timestamp indicating the last time the anonymous user
		with the given session_key rated the object."""
		raise NotImplementedError() # pragma: no cover
		#return datetime.utcnow()

	@property
	def most_recent(self):
		""" We don't track this and don't use it. """
		# But it is a validated part of the interface, so we can't raise
		return None
