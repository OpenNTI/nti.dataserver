#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support functions for reading objects.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import cgi
import six
import sys
import collections

from zope import component

from pyramid import httpexceptions as hexc

from nti.app.externalization import MessageFactory as _

from nti.app.externalization.error import handle_possible_validation_error

from nti.dataserver.interfaces import IDataserver

from nti.externalization.interfaces import IExternalRepresentationReader

from nti.externalization.internalization import find_factory_for
from nti.externalization import update_from_external_object

from nti.mimetype.mimetype import nti_mimetype_class

logger = __import__('logging').getLogger(__name__)


def create_modeled_content_object(unused_dataserver, owner, datatype, externalValue, unused_creator):
    """
    :param owner: The entity which will contain the object.
    :param creator: The user attempting to create the object. Possibly separate from the
            owner. Permissions will be checked for the creator
    """
    # The datatype can legit be null if we are MimeType-only
    if externalValue is None:
        return None

    result = None
    if datatype is not None and owner is not None:
        result = owner.maybeCreateContainedObjectWithType(datatype,
                                                          externalValue)

    if result is None:
        result = find_factory_for(externalValue)
        if result:
            result = result()
    return result


def class_name_from_content_type(request):
    """
    :return: The class name portion of one of our content-types, or None
            if the content-type doesn't conform. Note that this will be lowercase.
    """
    content_type = request
    if hasattr(request, 'content_type'):
        content_type = request.content_type
    content_type = content_type or ''
    return nti_mimetype_class(content_type)


def handle_unicode(value, request):
    if isinstance(value, six.text_type):  # already unicode
        return value
    try:
        value = value.decode(request.charset)
    except UnicodeError:
        # Try the most common web encoding
        value = value.decode('iso-8859-1')
    return value
_handle_unicode = handle_unicode


def read_input_data(input_data, request, reader=None, ext_format='json'):
    if reader is None:
        reader = component.getUtility(IExternalRepresentationReader,
									  name=ext_format)
    __traceback_info__ = input_data
    value = handle_unicode(input_data, request)
    result = reader.load(value)
    return result


def _is_file_upload(value):
    return   isinstance(value, (cgi.FieldStorage, cgi.MiniFieldStorage)) \
          or (hasattr(value, 'type') and hasattr(value, 'file'))


def _reset_file_pointer(value):
    fp = getattr(value, "fp", value)
    if hasattr(fp, 'seek'):
        fp.seek(0)


def _handle_content_type(reader, input_data, request, content_type):
    if content_type == 'multipart/form-data' and request.POST:
        # We parse the form-data and parse out all the non FieldStorage fields
        # which we leave in the original request for later processing
        # We return a dict with the form data
        result = dict()
        data = request.POST
        for key, value in data.items():
            if _is_file_upload(value):
                _reset_file_pointer(value)
            elif key in ('__json__', '__input__'):  # special case for embedded json data
                json_data = read_input_data(value, request)
                assert isinstance(json_data, collections.Mapping)
                result.update(json_data)
            else:
                result[handle_unicode(key, request)] = value
    else:
        # We need all string values to be unicode objects. simplejson is different from
        # the built-in json and returns strings
        # that can be represented as ascii as str objects if the input was a bytestring.
        # The only way to get it to return unicode is if the input is unicode, or
        # to use a hook to do so incrementally. The hook saves allocating the entire request body
        # as a unicode string in memory and is marginally faster in some cases. However,
        # the hooks gets to be complicated if it correctly catches everything (inside arrays,
        # for example; the function below misses them) so decoding to unicode up front
        # is simpler
        # def _read_body_strings_unicode(pairs):
        #     return dict( ( (k, (unicode(v, request.charset) if isinstance(v, str) else v))
        #                    for k, v
        #                    in pairs) )
        result = read_input_data(input_data, request, reader)

    return result


def read_body_as_external_object(request, input_data=None,
                                 expected_type=collections.Mapping):
    """
    Returns the object specified by the external data. The request input stream is
    input stream is parsed, and the return value is verified to be of `expected_type`

    :param input_data: If given, this is read instead of the request's body.

    :raises hexc.HTTPBadRequest: If there is an error parsing/transforming the
                    client request.
    """
    ext_format = 'json'
    value = input_data if input_data is not None else request.body
    content_type = getattr(request, 'content_type', None) or u''
    if (   content_type.endswith('plist')
        or content_type == 'application/xml'
        or request.GET.get('format') == 'plist'):  # pragma: no cover
        ext_format = 'plist'

    __traceback_info__ = ext_format, value
    reader = component.queryUtility(IExternalRepresentationReader,
								    name=ext_format)
    if reader is None:  # pragma: no cover
        # We're officially dropping support for plist values.
        # primarily due to the lack of support for null values, and
        # unsure about encoding issues
        raise hexc.HTTPUnsupportedMediaType(_(u"XML no longer supported."))

    try:
        value = _handle_content_type(reader, value, request, content_type)
        if not isinstance(value, expected_type):
            raise TypeError(type(value))
        return value
    except hexc.HTTPException:  # pragma: no cover
        raise
    except Exception:  # pragma: no cover
        # Sadly, there's not a good exception list to catch.
        # plistlib raises undocumented exceptions from xml.parsers.expat
        # json may raise ValueError or other things, depending on implementation.
        # transformInput may raise TypeError if the request is bad, but it
        # may also raise AttributeError if the inputClass is bad, but that
        # could also come from other places. We call it all client error.
        # Note that value could be a byte string at this point if decoding failed,
        # so be careful not to try to log it as a string
        logger.exception("Failed to parse/transform value %r", value)
        tb = sys.exc_info()[2]
        ex = hexc.HTTPBadRequest(_(u"Failed to parse/transform input"))
        raise ex, None, tb


def update_object_from_external_object(contentObject,
                                       externalValue,
                                       notify=True,
                                       request=None,
                                       pre_hook=None):
    dataserver = component.queryUtility(IDataserver)
    try:
        __traceback_info__ = contentObject, externalValue
        return update_from_external_object(contentObject, externalValue,
                                           context=dataserver, notify=notify,
                                           pre_hook=pre_hook)
    except Exception as e:
        handle_possible_validation_error(request, e)
