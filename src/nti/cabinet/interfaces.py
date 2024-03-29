#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class

from zope import interface

from zope.file.interfaces import IFileReader

from zope.location.interfaces import IContained

from nti.base.interfaces import DEFAULT_CONTENT_TYPE

from nti.base.interfaces import INamedFile

from nti.schema.field import Number
from nti.schema.field import TextLine
from nti.schema.field import DecodingValidTextLine


class ISourceBucket(IContained):

    name = interface.Attribute("Bucket name")

    def enumerateChildren():
        """
        return all children in this bucket
        """

    def getChildNamed(name):
        """
        return the child object with the specfied name
        """


class ISource(IFileReader, IContained, INamedFile):

    length = Number(title=u"Source length", required=False, default=None)

    contentType = DecodingValidTextLine(title=u'Content Type', required=False,
                                        default=DEFAULT_CONTENT_TYPE,
                                        missing_value=DEFAULT_CONTENT_TYPE)

    filename = TextLine(title=u"source file name", required=False)

    name = interface.Attribute("Source name")

    def getSize():
        """
        return the length of this source
        """

    def readContents():
        """
        read all the contents of this source
        """
IMultipartSource = ISource


class ISourceFiler(interface.Interface):

    default_bucket = interface.Attribute("Default bucket")

    def key_name(identifier):
        """
        return the key name for the specified identifier
        """

    def get_external_link(item):
        """
        return the external link of the specified item
        """

    def save(key, source, contentType=None, bucket=None, overwrite=False, **kwargs):
        """
        Save the specifed source in this filer object

        :param key: Source key identifier. (e.g. filename)
        :param source Source object to save. This object can be a python stream 
               or a :class:`.ISource` object
        :param contentType: Source content type
        :param bucket: Bucket (e.g subir) to write the source
        :param overwrite: Overite existing flag
        :return A source URL or href
        """

    def get(key, bucket=None):
        """
        Return a source

        :param key source identifier, href or url
        :param bucket: Optional bucket name (e.g subir)
        :return Source object or stream
        """

    def contains(self, key, bucket=None):
        """
        Check a source with the specifed key exists in this filer

        :param key: Source identifier, href or url
        :param bucket: Optional bucket name (e.g subir)
        """

    def remove(key, bucket=None):
        """
        Remove a source

        :param key source identifier, href or url
        :return True if source has been removed
        """

    def list(bucket=None):
        """
        listing of keys

        :param bucket: Bucket (e.g subir)
        """

    def is_bucket(key):
        """
        return if the specified key/url/href is a Bucket
        """
