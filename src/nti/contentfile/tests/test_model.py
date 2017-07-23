#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import all_of
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

from nti.testing.matchers import verifiably_provides

import unittest

from zope import interface

from zope.mimetype.interfaces import IContentTypeAware

from nti.contentfile.model import ContentBlobFile
from nti.contentfile.model import transform_to_blob

from nti.contentfile.interfaces import IContentBlobFile
from nti.contentfile.interfaces import IContentBlobImage

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.namedfile.interfaces import IInternalFileRef

from nti.contentfile.tests import SharedConfiguringTestLayer

from nti.externalization.tests import externalizes

GIF_DATAURL = b'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='


class TestModel(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_interface(self):
        assert_that(ContentBlobFile(name=u"cc", contentType='xx'),
                    verifiably_provides(IContentBlobFile))

    def test_name(self):
        internal = ContentBlobFile()
        internal.name = u'ichigo'
        assert_that(internal, has_property('name', is_('ichigo')))
        assert_that(internal, has_property('__name__', is_('ichigo')))

        internal.name = u'aizen'
        assert_that(internal, has_property('name', is_('aizen')))
        assert_that(internal, has_property('__name__', is_('aizen')))

    def test_file(self):
        ext_obj = {
            'MimeType': 'application/vnd.nextthought.contentimage',
            'value': GIF_DATAURL,
            'filename': u'ichigo.gif'
        }

        factory = find_factory_for(ext_obj)
        assert_that(factory, is_not(none()))

        internal = factory()
        update_from_external_object(internal, ext_obj, require_updater=True)

        assert_that(IContentTypeAware.providedBy(internal), is_(True))

        # value changed to URI
        assert_that(ext_obj, has_key('url'))
        assert_that(ext_obj, does_not(has_key('value')))

        assert_that(internal, has_property('contentType', 'image/gif'))
        assert_that(internal, has_property('filename', 'ichigo.gif'))
        assert_that(internal, has_property('name', 'ichigo.gif'))

        assert_that(internal.has_associations(), is_(False))

        assert_that(internal,
                    externalizes(all_of(has_key('CreatedTime'),
                                        has_key('Last Modified'),
                                        has_entry('name', 'ichigo.gif'),
                                        has_entry('FileMimeType', 'image/gif'),
                                        has_entry('MimeType', 'application/vnd.nextthought.contentimage'))))

        assert_that(internal, has_property('__name__', is_('ichigo.gif')))
        internal.name = 'foo'
        assert_that(internal, has_property('__name__', is_('foo')))

        internal.reference = 'oid'
        interface.alsoProvides(internal, IInternalFileRef)
        blob = transform_to_blob(internal, associations=True)
        assert_that(blob, verifiably_provides(IContentBlobImage))
        assert_that(IInternalFileRef.providedBy(blob), is_(True))
        assert_that(blob, has_property('reference', is_('oid')))
        assert_that(blob, has_property('name', is_('foo')))
        assert_that(blob, has_property('filename', is_('ichigo.gif')))
        assert_that(blob, has_property('contentType', is_('image/gif')))
        assert_that(blob, has_property('data', not_none()))
        assert_that(blob, has_property('size', is_(61)))

    def test_s3_file(self):
        ext_obj = {
            'MimeType': 'application/vnd.nextthought.s3file',
            'value': GIF_DATAURL,
            'filename': u'ichigo.gif'
        }

        factory = find_factory_for(ext_obj)
        assert_that(factory, is_not(none()))

        internal = factory()
        update_from_external_object(internal, ext_obj, require_updater=True)

        assert_that(IContentTypeAware.providedBy(internal), is_(True))

        # value changed to URI
        assert_that(ext_obj, has_key('url'))

        assert_that(internal, has_property('contentType', 'image/gif'))
        assert_that(internal, has_property('filename', 'ichigo.gif'))
        assert_that(internal, has_property('name', 'ichigo.gif'))

    def test_s3_image(self):
        ext_obj = {
            'MimeType': 'application/vnd.nextthought.s3image',
            'value': GIF_DATAURL,
            'filename': u'ichigo.gif'
        }

        factory = find_factory_for(ext_obj)
        assert_that(factory, is_not(none()))

        internal = factory()
        update_from_external_object(internal, ext_obj, require_updater=True)

        assert_that(IContentTypeAware.providedBy(internal), is_(True))

        # value changed to URI
        assert_that(ext_obj, has_key('url'))

        assert_that(internal, has_property('contentType', 'image/gif'))
        assert_that(internal, has_property('filename', 'ichigo.gif'))
        assert_that(internal, has_property('name', 'ichigo.gif'))
