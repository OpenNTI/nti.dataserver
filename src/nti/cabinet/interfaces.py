#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.file.interfaces import IFileReader

from zope.location.interfaces import IContained

from nti.schema.field import Number
from nti.schema.field import TextLine


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


class ISource(IFileReader, IContained):

    length = Number(title="Source length", required=False, default=None)

    contentType = TextLine(title="content type", required=False,
                           default=u'application/octet-stream')

    filename = TextLine(title="source file name", required=False)

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

    def key_name(self, identifier):
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
