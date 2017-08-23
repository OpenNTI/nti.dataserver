#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
An implementation of rating adapters.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations

from zope.event import notify

from pyramid.threadlocal import get_current_request

from persistent.interfaces import IPersistent

from contentratings.category import BASE_KEY

from contentratings.events import ObjectRatedEvent

from contentratings.interfaces import IUserRating
from contentratings.interfaces import IObjectRatedEvent

from contentratings.rating import NPRating

from contentratings.storage import UserRatingStorage

from nti.dataserver.interfaces import IRatable
from nti.dataserver.interfaces import ILastModified
from nti.dataserver.interfaces import IMemcacheClient

from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.oids import to_external_oid

from nti.externalization.singleton import SingletonDecorator

RATING_CAT_NAME = u'rating'


class IObjectUnratedEvent(IObjectRatedEvent):
    pass


@interface.implementer(IObjectUnratedEvent)
class ObjectUnratedEvent(ObjectRatedEvent):
    pass


def lookup_rating_for_read(context, cat_name, safe=False):
    """
    :param context: Something that is :class:`.ILikeable`
            and, for now, can be adapted to an :class:`contentratings.IUserRating`
            with the name of `cat_name`.
    :param string cat_name: The name of the ratings category to look up. One of
            :const:`LIKE_CAT_NAME` or :const:`FAVR_CAT_NAME`.
    :keyword bool safe: If ``False`` (the default) then this method can raise an
            exception if it won't ever be possible to rate the given object (because
            annotations and adapters are not set up). If ``True``, then this method
            quetly returns None in that case.
    :return: A user rating object, if one already exists. Otherwise :const:`None`.
    """

    # While we're using the default storage objects, as soon as they
    # are created the annotations are set, which can lead to too many conflicts.
    # we thus try to defer that.
    # This is a duplication of code from contentratings.cagetory

    # Get the key from the storage, or use a default
    key = getattr(UserRatingStorage, 'annotation_key', BASE_KEY)
    # Append the category name to the dotted annotation key name
    key = str(key + '.' + cat_name)
    # Retrieve the storage from the annotation. Note that IAttributeAnnotatable
    # default adapter does not create a OOBTree and set the __annotations__ attribute
    # until it is written to, so this is safe
    try:
        if not safe:
            annotations = IAnnotations(context)
        else:
            annotations = IAnnotations(context, {})
        storage = annotations.get(key)
        if storage:
            # Ok, we already have one. Use it.
            return lookup_rating_for_write(context, cat_name=cat_name)
    except (TypeError, LookupError):
        if not safe:
            raise


def lookup_rating_for_write(context, cat_name):
    return component.getAdapter(context, IUserRating, name=cat_name)


def rate_object(context, username, rating, cat_name=RATING_CAT_NAME):
    storage = lookup_rating_for_write(context, cat_name)
    return storage.rate(rating, username)


def unrate_object(context, username, cat_name=RATING_CAT_NAME):
    old_rating = None
    storage = lookup_rating_for_read(context, cat_name)
    if storage:
        old_rating = storage.userRating(username)
        if old_rating is not None:
            storage.remove_rating(username)
            # NOTE: The default implementation of a category does not
            # fire an event on unrating, so we do.
            # Must include the rating so that the listeners can know who did it
            notify(ObjectUnratedEvent(context, old_rating, cat_name))
    return storage, old_rating


def get_object_rating(context, username, cat_name, safe=False, default=None):
    result = default
    rating = lookup_rating_for_read(context, cat_name=cat_name, safe=safe)
    if rating is not None:
        user_rating = rating.userRating(username)
        result = user_rating if user_rating is not None else default
    return result


def cached_decorator(key_func):

    def factory(func):
        @functools.wraps(func)
        def _caching(*args, **kwargs):
            key = key_func(*args, **kwargs)
            if key:
                cache = component.queryUtility(IMemcacheClient)
                if cache is not None:
                    try:
                        cached = cache.get(key)
                        if cached is not None:
                            return cached
                    except Exception as e:
                        logger.error("Cannot get Memcache value for key %s. %s",
                                     key, e)
                        cached = None

            result = func(*args, **kwargs)
            if key and cache is not None:
                __traceback_info__ = key, result, cache
                cache.set(key, result)
            return result
        return _caching
    return factory


def generic_cache_key(context, cat_name, path):
    try:
        oid = to_external_oid(context)
        return (oid + '/@@' + cat_name + '/' + path).encode('utf-8')
    except TypeError:  # to_external_oid throws if context not saved
        return None


def _rate_count_cache_key(context, cat_name):
    return generic_cache_key(context, cat_name, 'count')


@cached_decorator(_rate_count_cache_key)
def rate_count(context, cat_name):
    """
    Return the number of times this object has been rated the particular way.
    Accepts any object, not just those that can be rated.
    """
    ratings = lookup_rating_for_read(context, cat_name, safe=True)
    result = ratings.numberOfRatings if ratings else 0
    return result


def _rating_object_cache_key(context, username):
    return generic_cache_key(context, RATING_CAT_NAME, username)


@cached_decorator(_rating_object_cache_key)
def rates_object(context, username):
    """
    Determine if the `username` has rated the `context`.

    :param context: An :class:`~.IRatable` object.
    :param username: The name of the user that has rated the object.
    :return: An object with a rating value;
    """
    result = get_object_rating(context, username, RATING_CAT_NAME)
    if result is not None and IPersistent.providedBy(result):
        result = NPRating(float(result), username)
    return result


@component.adapter(IRatable)
@interface.implementer(IExternalMappingDecorator)
class RatingDecorator(object):

    __metaclass__ = SingletonDecorator

    def decorateExternalMapping(self, context, mapping):
        request = get_current_request()
        username = request.authenticated_userid if request else None
        if username:
            rating = rates_object(context, username)
            if rating is not None:
                mapping['Rating'] = float(rating)


def update_last_mod(modified_object, unused_event=None):
    """
    When an object is rated (or unrated), its last modified time, and
    that of its parent, should be updated.
    """

    # An alternative to this would be to transform IObjectRatedEvent
    # into IObjectModified event and let the normal handlers for that take over.
    # But (in the future) there may be listeners to ObjectModified that do other
    # things we wouldn't want to happen for a rating

    last_mod = modified_object.updateLastMod()
    try:
        modified_object.__parent__.updateLastMod(last_mod)
    except AttributeError:
        # not contained or not contained in a ILastModified container
        pass


@component.adapter(ILastModified, IObjectRatedEvent)
def update_last_mod_on_rated(modified_object, event):
    update_last_mod(modified_object, event)
    cache = component.queryUtility(IMemcacheClient)
    if cache:
        try:
            key = _rate_count_cache_key(modified_object, event.category)
            cache.delete(key)
        except cache.MemcachedKeyNoneError:  # not saved yet
            pass
