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
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

import contentratings.interfaces

from nti.dataserver import interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator

from . import ratings

#: Category name for liking; use this as the name of the adapter
LIKE_CAT_NAME = 'likes'

#: Category name for favorites; use this as the name of the adapter
FAVR_CAT_NAME = 'favorites'

_cached = ratings.cached_decorator

def _lookup_like_rating_for_read(context, cat_name=LIKE_CAT_NAME, safe=False):
	return ratings.lookup_rating_for_read(context, cat_name, safe)

def _lookup_like_rating_for_write(context, cat_name=LIKE_CAT_NAME):
	return ratings.lookup_rating_for_write(context, cat_name)

def _rates_object(context, username, cat_name, safe=False):
	result = ratings.get_object_rating(context, username, safe=safe, default=False)
	return result

# We define likes simply as a rating of 1, and unlikes remove
# the user from the list.
# Favorites, aka Bookmarks, are implemented the same way. This has the advantage
# of keeping it all object-local; the disadvantage that an index is required to
# have the user query for his favorites (such an index can be maintained
# by listening for the ObjectRatedEvents sent by a RatingCategory; NOTE: this
# only seems to fire when ratings are added, not when ratings are removed so it's not
# quite sufficient to maintain an index). Our _unrate_object method fires
# such an event...the rating value will be None, so that's how a listener can
# distinguish "rating added" from "rating removed"

def _rate_object(context, username, cat_name):
	rating = ratings.lookup_rating_for_write(context, cat_name)
	if rating.userRating( username ) is None:
		rating.rate( 1, username )
		return rating

def _unrate_object(context, username, cat_name):
	rating, old_rating = ratings.unrate_object(context, username, cat_name)
	if old_rating is not None:
		assert int(old_rating) is 0
		return rating

def like_object( context, username ):
	"""
	Like the `context` idempotently.

	:param context: An :class:`~.ILikeable` object.
	:param username: The name of the user liking the object. Should not be
		empty.
	:return: An object with a boolean value; if action was taken, the value is True-y.
	:raises TypeError: If the `context` is not really likeable.
	"""
	return _rate_object( context, username, LIKE_CAT_NAME )

def unlike_object(context, username):
	"""
	Unlike the `object`, idempotently.

	:param context: An :class:`~.ILikeable` object.
	:param username: The name of the user liking the object. Should not be
		empty.
	:return: An object with a boolean value; if action was taken, the value is True-y.
	:raises TypeError: If the `context` is not really likeable.
	"""
	return _unrate_object(context, username, LIKE_CAT_NAME)

def _likes_object_cache_key(context, username):
	return ratings.generic_cache_key(context, LIKE_CAT_NAME, username)

@_cached(_likes_object_cache_key)
def likes_object( context, username ):
	"""
	Determine if the `username` likes the `context`.

	:param context: An :class:`~.ILikeable` object.
	:param username: The name of the user liking the object. Should not be
		empty.
	:return: An object with a boolean value; if the user likes the object, the value
		is True-y.
	"""
	result = _rates_object(context, username, LIKE_CAT_NAME)
	return result

def like_count( context ):
	"""
	Determine how many distinct users like the `context`.

	:param context: Any object (unlike the rest of the functions, this is
		not limited to just :class:`~.ILikeable` objects).
	:return: A non-negative integer.
	"""
	return ratings.rate_count(context, LIKE_CAT_NAME)

def favorite_object(context, username):
	"""
	Favorite the `context` idempotently.

	:param context: An :class:`~.IFavoritable` object.
	:param username: The name of the user favoriting the object. Should not be
		empty.
	:return: An object with a boolean value; if action was taken, the value is True-y.
	:raises TypeError: If the `context` is not really likeable.
	"""
	return _rate_object(context, username, FAVR_CAT_NAME)

def unfavorite_object(context, username):
	"""
	Unfavorite the ``object``, idempotently.

	:param context: An :class:`~.IFavoritable` object.
	:param username: The name of the user unfavoriting the object. Should not be
		empty.
	:return: An object with a boolean value; if action was taken, the value is True-y.
	:raises TypeError: If the `context` is not really likeable.
	"""
	return _unrate_object(context, username, FAVR_CAT_NAME)

def _favorites_object_cache_key(context, username, safe=False):
	return ratings.generic_cache_key(context, FAVR_CAT_NAME, username)

@_cached(_favorites_object_cache_key)
def favorites_object(context, username, safe=False):
	"""
	Determine if the ``username`` has favorited the ``context``.

	:param context: An :class:`~.IFavoritable` object.
	:param username: The name of the user possibly favoriting the object. Should not be
		empty.
	:keyword bool safe: If ``False`` (the default) then this method can raise an
		exception if it won't ever be possible to rate the given object (because
		annotations and adapters are not set up). If ``True``, then this method
		quetly returns ``False`` in that case.

	:return: An object with a boolean value; if the user likes the object, the value
		is True-y.
	"""
	return _rates_object(context, username, FAVR_CAT_NAME, safe=safe)


@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(interfaces.ILikeable)
class LikeDecorator(object):
	"""
	For :class:`~.ILikeable` objects, records the number of times they
	have been liked in the ``LikeCount`` value of the external map.
	"""
	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, context, mapping):
		mapping['LikeCount'] = like_count( context ) # go through the function to be safe


from zope.container.contained import Contained

import BTrees
from BTrees.Length import Length

from persistent import Persistent

from contentratings.rating import NPRating

@interface.implementer(contentratings.interfaces.IUserRating,
					   contentratings.interfaces.IRatingStorage)
class _BinaryUserRatings(Contained, Persistent):
	"""
	BTree-based storage for binary user ratings, where a user can either have rated
	(with a 1) or not; no other value is permitted. Furthermore, the anonymous
	user is prohibited. This allows for optimizations in
	storage and implementation.

	Compare with :class:`contentratings.storage.UserRatingStorage` for a full
	implementation.
	"""

	scale = 1

	def __init__(self):
		super(_BinaryUserRatings,self).__init__()
		# Since we are simply recording the presence or absence of a user,
		# can can use a simple set of strings
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

		return NPRating( 1, username )

	def userRating(self, username=None):
		"""Retreive the rating for the specified user, which must be provided."""
		if not username:  #pragma: no cover
			raise ValueError( "Must give username" )
		if username in self._ratings:
			return NPRating( 1, username )

	def remove_rating(self, username):
		"""Remove the rating for a given user"""
		self._ratings.remove(username)
		self._length.change(-1)
		return NPRating( 0, username )

	def all_user_ratings(self, include_anon=False):
		"""
		:param bool include_anon: Ignored.
		"""
		return (NPRating( 1, username) for username in self.all_raters)

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

@component.adapter(interfaces.ILastModified, contentratings.interfaces.IObjectRatedEvent)
def update_last_mod_on_rated( modified_object, event ):
	cache = component.queryUtility(interfaces.IMemcacheClient)
	if cache:
		try:
			if event.category == LIKE_CAT_NAME:
				key_func = _likes_object_cache_key
			elif event.category == FAVR_CAT_NAME:
				key_func = _favorites_object_cache_key
			cache.delete(key_func(modified_object, event.rating.userid))
		except cache.MemcachedKeyNoneError: # not saved yet
			pass
