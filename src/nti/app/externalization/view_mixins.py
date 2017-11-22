#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities relating to views.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import sys
import copy
import datetime
import operator
import transaction

from Acquisition import aq_base

from zope import interface

from zope.schema.interfaces import ValidationError

from z3c.batching.batch import Batch

from ZODB.POSException import POSError

from pyramid import httpexceptions as hexc

from pyramid import traversal

import webob.datetime_utils

from nti.app.externalization import MessageFactory as _

from nti.app.externalization.error import handle_validation_error
from nti.app.externalization.error import handle_possible_validation_error

from nti.app.externalization.internalization import read_body_as_external_object
from nti.app.externalization.internalization import create_modeled_content_object
from nti.app.externalization.internalization import update_object_from_external_object

from nti.base._compat import text_

from nti.base.interfaces import DEFAULT_CONTENT_TYPE

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.externalization.externalization import to_standard_external_last_modified_time

from nti.externalization.interfaces import StandardExternalFields

from nti.links.links import Link

from nti.mimetype import mimetype

from nti.zodb import isBroken

ID = StandardExternalFields.ID
CLASS = StandardExternalFields.CLASS
ITEMS = StandardExternalFields.ITEMS
MIMETYPE = StandardExternalFields.MIMETYPE
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

_marker = object()
_tuple_selector = operator.itemgetter(1)

logger = __import__('logging').getLogger(__name__)


class BatchingUtilsMixin(object):
    """
    A mixin class that can be added to view classes to
    provide sort for batching items. The subclass defines the
    ``request`` attribute.
    """

    _DEFAULT_BATCH_SIZE = None
    _DEFAULT_BATCH_START = None

    def _get_batch_size_start(self):
        """
        Return a two-tuple, (batch_size, batch_start). If the values are
        invalid, raises an HTTP exception. If either is missing, returns
        the defaults for both.
        """
        batch_size = self.request.params.get('batchSize',
                                             self._DEFAULT_BATCH_SIZE)
        batch_start = self.request.params.get('batchStart',
                                              self._DEFAULT_BATCH_START)
        if batch_size is not None and batch_start is not None:
            try:
                batch_size = int(batch_size)
                batch_start = int(batch_start)
            except ValueError:
                raise hexc.HTTPBadRequest("Batch size/start not integers")
            if batch_size <= 0 or batch_start < 0:
                raise hexc.HTTPBadRequest("Batch size/start out of range")

            return batch_size, batch_start

        return self._DEFAULT_BATCH_SIZE, self._DEFAULT_BATCH_START

    # A sequence of names of query params that will be dropped from
    # links we generate for batch-next and batch-prev, typically
    # because they do not have relevance in a next/prev query.
    _BATCH_LINK_DROP_PARAMS = ('batchAround', 'batchContaining', 'batchBefore')

    @classmethod
    def _create_batch_links(cls, request, result, next_batch_start, prev_batch_start):
        for batch, rel in ((next_batch_start, 'batch-next'),
                           (prev_batch_start, 'batch-prev')):
            if batch is not None:
                batch_params = request.GET.copy()
                # Pop some things that don't work
                for n in cls._BATCH_LINK_DROP_PARAMS:
                    batch_params.pop(n, None)

                batch_params['batchStart'] = batch
                # sort for reliable testing
                query = sorted(batch_params.items())
                link_next_href = request.current_route_path(_query=query)
                link_next = Link(link_next_href, rel=rel)
                result.setdefault('Links', []).append(link_next)

    def _set_batch_links(self, result, result_list, next_batch_start, prev_batch_start):
        self._create_batch_links(self.request, result,
                                 next_batch_start, prev_batch_start)
        return result_list

    @classmethod
    def _get_number_items_needed(cls, batch_size, batch_start, number_items_needed=_marker):
        if number_items_needed is _marker or number_items_needed is None:
            number_items_needed = batch_size + batch_start + 2
        return number_items_needed

    @classmethod
    def _batch_start_tuple(cls, batch_start, batch_size, number_items_needed=_marker):
        number_items_needed = cls._get_number_items_needed(batch_size,
                                                           batch_start,
                                                           number_items_needed)

        # Previous first. We want to try to go back exactly the page
        # size, otherwise to zero.
        if batch_start > 0:
            prev_batch_start = max(0, batch_start - batch_size)
        else:
            # No where to go back
            prev_batch_start = None

        # Next, we want to go to the batch exactly after this one, if
        # possible. It may not have a full page of data, though.
        # Note that we always count on having at least a few extra items
        if batch_start + batch_size < number_items_needed:
            next_batch_start = batch_start + batch_size
        else:
            next_batch_start = None
        return prev_batch_start, next_batch_start

    def __batch_result_list(self, result, result_list,
                            batch_start, batch_size,
                            number_items_needed):
        # These may have changed from the request params, or be
        # defaults, tell the client what we really used if we generate
        # links
        self.request.GET['batchSize'] = str(batch_size)
        self.request.GET['batchStart'] = str(batch_start)

        if batch_start >= len(result_list):
            # Batch raises IndexError in this case, avoid that
            return []
        batch_result = Batch(result_list, batch_start, batch_size)

        # Insert links to the next and previous batch
        # NOTE: If our batch_start is not a multiple of the batch_size,
        # then using IBatch.next and IBatch.previous fails as it expects
        # to the index of the batch to correlate with the previous
        # batch start. So we manually do the math for start
        prev_batch_start, next_batch_start = self._batch_start_tuple(batch_start,
                                                                     batch_size,
                                                                     number_items_needed)

        self._set_batch_links(result, batch_result,
                              next_batch_start, prev_batch_start)

        return batch_result

    def _is_valid(self, x):
        result = (x is not None and not isBroken(x))
        return result

    def _batch_items_iterable(self,
                              result,
                              items,
                              number_items_needed=_marker,
                              batch_size=_marker,
                              batch_start=_marker,
                              selector=lambda x: x,
                              ignore_invalid=False):
        """
        Handle batching in a flexible way.

        :param dict result: The dictionary in which we place the `Items` sequence
                and possibly links for next/previous batch.
        :param items: A sequence of the objects to batch. This may be a
                generator or other iterator; we promise to only traverse it once,
                and not need to get its length.
        :keyword selector: This callable is applied to each element of the items sequence
                to produce the final item in the batch.
        :param ignore_invalid: Flag to ignore missing or broken objects.
        """

        def _trax(item):
            try:
                x = selector(item)
                x = x if not ignore_invalid or self._is_valid(x) else None
                return x
            except (KeyError, POSError):
                if not ignore_invalid:
                    raise

        if batch_size is _marker and batch_start is _marker:
            batch_size, batch_start = self._get_batch_size_start()

        if batch_size is None or batch_start is None:
            # Not batching.
            result_list = []
            for x in items:
                x = _trax(x)
                if x is not None:
                    result_list.append(x)
            result[ITEMS] = result_list
            return result

        # Ok, reify up to batch_size + batch_start + 2 items from merged
        number_items_needed = self._get_number_items_needed(batch_size,
                                                            batch_start,
                                                            number_items_needed)

        count = 0
        result_list = []
        for x in items:
            x = _trax(x)
            if x is not None:
                count += 1
                result_list.append(x)
                if count > number_items_needed:
                    break

        result['BatchPage'] = batch_start // batch_size + 1
        batched_results = self.__batch_result_list(result,
                                                   result_list,
                                                   batch_start,
                                                   batch_size,
                                                   number_items_needed)
        result[ITEMS] = batched_results
        result[ITEM_COUNT] = len(batched_results)
        return result

    def _batch_tuple_iterable(self, *args, **kwargs):
        """
        Like :meth:`_batch_items_iterable` except we default to the items iterator
        being a sequence of tuples, like come from a dictionary's `items` method,
        or have been used to sort with an auxiliary key in position 0.
        """
        if 'selector' not in kwargs:
            kwargs['selector'] = _tuple_selector
        return self._batch_items_iterable(*args, **kwargs)

    def _batch_on_item(self, iterator, test, batch_containing=False,
                       batch_after=False, batch_before=False):
        """
        Given an iterator of items, and a test function that returns true when the desired
        batch-around item is found, handle the batching. The request params for
        `batchStart` and `batchSize` will be updated, so any cached values should be
        discarded. We only do this if `batchSize` is given. If not found, we return an empty
        list. By default, we will return the batch `around` a given item.  Optionally, we
        can return the batch after an item, or the natural batch (or page) containing
        the item.

        :batch_containing: (Optional) If true, do not batch the found item in the center
                of a given page. Instead, return the natural page (given by batchSize) that
                the given element would be found in.

        :batch_after: (Optional) If true, batch after the found item.

        :batch_before: (Optional) If true, batch before the found item.

        :return: A sequence of the items consumed from the iterator to find the
                object to center the batch on. Note that this may be every object
                if we did not find the creator. If no batch size was given, this
                will be the iterator.
        """
        batch_size, batch_start = self._get_batch_size_start()
        if not batch_size:
            return []

        number_items_needed = batch_start + batch_size + 2
        # Ok, they have requested that we compute a beginning index for them.
        # We do this by materializing the list in memory and walking through
        # to find the index of the requested object.
        batch_start = None  # ignore input
        result_list = []
        match_index = None
        for i, key_value in enumerate(iterator):
            result_list.append(key_value)

            # Only keep testing until we find what we need
            if batch_start is None:
                if test(key_value):
                    if batch_containing:
                        # Find our natural page
                        batch_start = (i // batch_size) * batch_size
                    elif batch_after:
                        batch_start = i + 1
                    elif batch_before:
                        if i == 0:
                            # For the first element, return an empty page.
                            pass
                        elif i <= batch_size:
                            # Need to reduce our batch size to capture
                            # everything before our item.
                            self.request.GET['batchSize'] = str(i)
                            batch_start = 0
                        else:
                            batch_start = i - batch_size
                    else:
                        batch_start = max(0, i - (batch_size // 2) - 1)
                    match_index = i
                    if batch_start is not None:
                        number_items_needed = batch_start + batch_size + 2
            else:
                # we found our match, it's in the list
                if i > number_items_needed:
                    # We can stop materializing now
                    break

        is_batch_around = not batch_containing \
                      and not batch_after \
                      and not batch_before

        if batch_start is None:
            # Well, we got here without finding the matching value.
            # So return an empty page.
            batch_start = len(result_list)
        elif is_batch_around and match_index <= batch_start:
            # For very small batches, when the match is at
            # the beginning of the list (typically),
            # we could wind up returning a list that doesn't include
            # the around value. Do our best to make sure that
            # doesn't happen.
            batch_start = max(0, match_index - (batch_size // 2))

        # Likewise, if the batch_size is very small and the match is at the end
        # typically with batch_size == 1
        if      match_index is not None \
            and not batch_before \
            and match_index >= batch_size + batch_start:
            batch_start = match_index

        if      is_batch_around \
            and batch_start is not None \
            and batch_size == 3 \
            and match_index is not None:
            # For non-even batch sizes, it's hard to evenly center
            # with generic math, or at least I'm stupid and missing what
            # the right algorithm is in all cases. Special case this
            # common size to get it right
            batch_start = max(0, match_index - 1)

        self.request.GET['batchStart'] = str(batch_start)
        return result_list


class UploadRequestUtilsMixin(object):
    """
    A mixin class that can be added to view classes to provide
    utility methods for working with the content of uploads, especially
    useful for supporting different types of uploads. The subclass must
    define the ``request`` attribute.
    """

    request = None

    def _find_file_field(self):
        """
        Find the object representing the file upload portion of a form POST (or PUT).
        Assumes there is only one, and if one is found it is returned. Otherwise
        None is returned.
        :return: An instance of :class:`cgi.FieldStorage` or None.
        """
        if self.request.content_type == 'multipart/form-data':
            # Expecting exactly one key in POST, the file
            field = None
            for k in self.request.POST:
                v = self.request.POST[k]
                if hasattr(v, 'type') and hasattr(v, 'file'):
                    # must be our field
                    field = v
                    break
            return field

    def _get_body_content(self):
        """
        Return the uploaded body content for the current request as a byte string.
        This will either be the POST'd file data, or the request body.
        """
        field = self._find_file_field()
        if field is not None:
            in_file = field.file
            in_file.seek(0)
            return in_file.read()
        return self.request.body

    def _get_body_type(self):
        """
        Returns a string giving the MIME type of the uploaded
        body (either the POST'd file or the request itself). If
        no type is given by the client, returns a generic type.
        """
        field = self._find_file_field()
        if field is not None:
            return field.type
        return self.request.content_type or text_(DEFAULT_CONTENT_TYPE)

    def _get_body_name(self):
        """
        Returns a string giving the name that the client would like to use
        for the uploaded body. This will either be the file name sent
        in the POST request, or the AtomPub ``Slug`` header. If no name
        is found, then an empty string is returned.
        """
        field = self._find_file_field()
        if field is not None and field.filename:
            return field.filename
        return self.request.headers.get('Slug') or ''


class ModeledContentUploadRequestUtilsMixin(object):
    """
    A mixin class that can be added to views to help working with
    uploading content that is parsed and treated as modeled content.
    The subclass defines the ``request`` attribute.
    """

    inputClass = dict
    content_predicate = id

    #: Subclasses can define this as a tuple of types to
    #: catch that we can't be sure are client or server errors.
    #: We catch TypeError and LookupError (which includes KeyError)
    #: by default, often they're a failed
    #: interface adaptation, but that could be because of bad input
    _EXTRA_INPUT_ERRORS = (TypeError, LookupError)

    def __call__(self):
        """
        Subclasses may implement a `_do_call` method if they do not override
        __call__.
        """
        try:
            return self._do_call()
        except ValidationError as e:
            transaction.doom()
            handle_validation_error(self.request, e)
        except interface.Invalid as e:
            transaction.doom()
            handle_possible_validation_error(self.request, e)
        except self._EXTRA_INPUT_ERRORS:  # pragma: no cover
            # These are borderline server/client errors. They could
            # be either, depending on details...
            transaction.doom()
            logger.warn("Failed to accept input. Client or server problem?", 
						exc_info=True)
            raise hexc.HTTPUnprocessableEntity(
                _("Unexpected internal error; see logs"))

    def readInput(self, value=None):
        """
        Returns the object specified by self.inputClass object. The data from the
        input stream is parsed, an instance of self.inputClass is created and update()'d
        from the input data.

        :raises hexc.HTTPBadRequest: If there is an error parsing/transforming the
                client request.
        """
        result = read_body_as_external_object(self.request,
                                              input_data=value,
                                              expected_type=self.inputClass)
        try:
            return self._transformInput(result)
        except hexc.HTTPException:
            raise
        except Exception:
            # Sadly, there's not a good exception list to catch.
            # plistlib raises undocumented exceptions from xml.parsers.expat
            # json may raise ValueError or other things, depending on implementation.
            # transformInput may raise TypeError if the request is bad, but it
            # may also raise AttributeError if the inputClass is bad, but that
            # could also come from other places. We call it all client error.
            logger.exception("Failed to parse/transform value %s", value)
            _, _, tb = sys.exc_info()
            ex = hexc.HTTPBadRequest("Failed to parse/transform value")
            raise ex, None, tb

    def _transformInput(self, value):
        return value

    def findContentType(self, externalValue):
        """
        Attempts to find the best content type (datatype), one that can be used with
        :meth:`createContentObject`.

        There are multiple places this can come from. In priority order, they are:

        * The ``MimeType`` value in the given data;
        * The ``ContentType`` header, if it names an NTI content type (any trailing +json will be removed);
        * Last, the ``Class`` value in the given data

        Note that this method can return either a simple class name, or a Mime type
        string.
        """

        if externalValue.get(MIMETYPE):
            return externalValue[MIMETYPE]

        if 	    self.request.content_type \
            and self.request.content_type.startswith(mimetype.MIME_BASE):
            datatype = self.request.content_type
            if datatype.endswith('+json'):
                datatype = datatype[:-5]  # strip +json
            if datatype and datatype != mimetype.MIME_BASE:  # prevent taking just the base type
                return datatype

        if externalValue.get(CLASS):
            return externalValue[CLASS] + 's'

    def createContentObject(self, user, datatype, externalValue, creator):
        return create_modeled_content_object(self.dataserver,
                                             user,
                                             datatype,
                                             externalValue,
                                             creator)

    def createAndCheckContentObject(self, owner, datatype, externalValue,
                                    creator, predicate=None):
        if predicate is None:
            predicate = self.content_predicate
        containedObject = self.createContentObject(owner, datatype,
                                                   externalValue, creator)
        if containedObject is None or not predicate(containedObject):
            transaction.doom()
            logger.debug("Failing to POST: input of unsupported/missing Class: %s %s => %s %s",
                         datatype, externalValue, containedObject, predicate)
            raise hexc.HTTPUnprocessableEntity(_('Unsupported/missing Class'))
        return containedObject

    def updateContentObject(self, contentObject, externalValue, set_id=False,
                            notify=True, pre_hook=None, object_hook=None):
        # We want to be sure to only change values on the actual content object,
        # not things in its traversal lineage
        containedObject = update_object_from_external_object(aq_base(contentObject),
                                                             externalValue,
                                                             notify=notify,
                                                             pre_hook=pre_hook,
                                                             request=self.request,
                                                             object_hook=object_hook)

        # If they provided an ID, use it if we can and we need to
        if      set_id and ID in externalValue \
            and hasattr(containedObject, ID) \
            and getattr(containedObject, ID, None) != externalValue[ID]:
            try:
                containedObject.id = externalValue['ID']
            except AttributeError:
                # It's OK if we cannot use the given ID; POST is meant
                # to auto-assign
                pass
        return containedObject

    def performReadCreateUpdateContentObject(self, user, search_owner=False, externalValue=None,
                                             deepCopy=False, add_to_connection=True):
        creator = user
        externalValue = self.readInput() if not externalValue else externalValue
        returnExternal = copy.deepcopy(
            externalValue) if deepCopy else externalValue
        datatype = self.findContentType(externalValue)

        context = self.request.context
        # If our context contains a user resource, then that's where we should be trying to
        # store things. This may be different than the creator if the remote
        # user is an administrator (TODO: Revisit this.)
        owner_root = None
        if search_owner:
            owner_root = traversal.find_interface(context, IUser)
            if owner_root is not None:
                owner_root = getattr(owner_root, 'user',
                                     owner_root)  # migration compat
            if owner_root is None:
                owner_root = traversal.find_interface(context, IUser)
            if owner_root is None and hasattr(context, 'container'):
                owner_root = traversal.find_interface(context.container, IUser)

        owner = owner_root if owner_root else creator

        containedObject = self.createAndCheckContentObject(owner,
                                                           datatype,
                                                           externalValue,
                                                           creator)
        if add_to_connection:
            containedObject.creator = creator
            # The process of updating may need to index and create KeyReferences
            # so we need to have a jar. We don't have a parent to inherit from just yet
            # (If we try to set the wrong one, it messes with some events and some
            # KeyError detection in the containers)
            # containedObject.__parent__ = owner
            owner_jar = getattr(owner, '_p_jar', None)
            if owner_jar and getattr(containedObject, '_p_jar', self) is None:
                owner_jar.add(containedObject)

        # Update the object, but don't fire any modified events. We don't know
        # if we'll keep this object yet, and we haven't fired a created event
        self.updateContentObject(containedObject, externalValue,
                                 set_id=True, notify=False)

        return (containedObject, owner, returnExternal)

    def readCreateUpdateContentObject(self, user, search_owner=False, externalValue=None):
        """
        Combines reading the external input, deriving the expected data
        type, creating the content object, and updating it in one step.

        :keyword bool search_owner: If set to True (not the default), we will
                look for a user along our context's lineage; the user
                will be used by default. It will be returned. If False,
                the return will only be the contained object.

        :keyword dict externalValue: External value use to create the content object

        """
        containedObject, owner, _ = self.performReadCreateUpdateContentObject(user,
                                                                              search_owner,
                                                                              externalValue)
        return (containedObject, owner) if search_owner else containedObject


class ModeledContentEditRequestUtilsMixin(object):
    """
    A mixin class that can be added to views that are editing new
    or existing objects.
    """

    def _to_utc(self, last_mod):
        return datetime.datetime.fromtimestamp(last_mod, webob.datetime_utils.UTC)

    def _check_object_exists(self, o, cr='', cid='', oid=''):
        """
        If the first argument is None or has been deleted (is marked
        with :class:`IDeletedObjectPlaceholder`), raises a 404 error.
        The remaining arguments are used as details in the message.
        """
        if o is None or IDeletedObjectPlaceholder.providedBy(o):
            raise hexc.HTTPNotFound("No object %s/%s/%s" % (cr, cid, oid))

    def _check_object_unmodified_since(self, obj):
        """
        If the request for this object has a 'If-Unmodified-Since' header,
        and the provided object supports modification times, then the two
        values will be compared, and if the objects modification time is
        more recent than the request's, HTTP's 412 Precondition failed will be
        raised.
        """

        if self.request.if_unmodified_since is not None:
            obj_last_mod = to_standard_external_last_modified_time(obj)
            if      obj_last_mod is not None \
                and self._to_utc(obj_last_mod) > self.request.if_unmodified_since:
                raise hexc.HTTPPreconditionFailed()

    def _check_object_constraints(self, obj, externalValue):
        pass
