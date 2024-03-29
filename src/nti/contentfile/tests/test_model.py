#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import none
from hamcrest import all_of
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import instance_of
does_not = is_not

from nti.testing.matchers import verifiably_provides

import unittest

from BTrees.OOBTree import OOTreeSet

from functools import total_ordering

from zope import interface

from zope.mimetype.interfaces import IContentTypeAware

from persistent import Persistent

from persistent.list import PersistentList

from nti.contentfile.interfaces import IS3File
from nti.contentfile.interfaces import IS3Image
from nti.contentfile.interfaces import IContentBlobFile
from nti.contentfile.interfaces import IContentBlobImage

from nti.contentfile.model import ContentBlobFile
from nti.contentfile.model import transform_to_blob

from nti.contentfile.tests import SharedConfiguringTestLayer

from nti.externalization.internalization import find_factory_for
from nti.externalization import update_from_external_object

from nti.externalization.tests import externalizes

from nti.namedfile.interfaces import IInternalFileRef

from nti.wref.interfaces import IWeakRef


GIF_DATAURL = 'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='

# Note we need total_ordering for this test
        # because we are testing the migration of the old OOTreeSet structure
        # If we don't do that this test will fail on PURE_PYTHON
        # The new implementation doesn't require IWeakRef implementations
        # to have total ordering.
@total_ordering
@interface.implementer(IWeakRef)
class _WRef(object):

    def __init__(self, key, _refs):
        self._refs = _refs
        self.key = key

    def __call__(self):
        return self._refs.get(self.key, None)

    def __eq__(self, other):
        return self.key == other.key

    def __lt__(self, other):
        return self.key < other.key

class TestModel(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_interface(self):
        assert_that(ContentBlobFile(name=u"cc", contentType='xx'),
                    verifiably_provides(IContentBlobFile))

    def test_name(self):
        internal = ContentBlobFile()
        internal.filename = u'ichigo'
        assert_that(internal, has_property('name', is_('ichigo')))
        assert_that(internal, has_property('filename', is_('ichigo')))
        assert_that(internal, has_property('__name__', is_('ichigo')))

        internal.__name__ = u'aizen'
        assert_that(internal, has_property('filename', is_('aizen')))
        assert_that(internal, has_property('__name__', is_('aizen')))

        internal.name = u'zaraki'
        assert_that(internal, has_property('name', is_('zaraki')))
        assert_that(internal, has_property('filename', is_('aizen')))
        assert_that(internal, has_property('__name__', is_('aizen')))

    def test_associations(self):
        class Base(Persistent):
            pass

        base = Base()
        ref = IWeakRef(base)

        internal = ContentBlobFile()
        internal.filename = u'ichigo'

        assert_that(internal.add_association(ref),
                    is_(True))

        assert_that(internal.has_associations(),
                    is_(True))

        assert_that(internal.count_associations(),
                    is_(1))

        assert_that(internal.add_association(ref),
                    is_(False))

        internal.validate_associations()
        assert_that(internal.count_associations(),
                    is_(1))

        internal.remove_association(ref)
        assert_that(internal.count_associations(),
                    is_(0))

        assert_that(internal.has_associations(),
                    is_(False))

    def test_associations_maintenance(self):

        refs = dict()

        refs['a'] = 'A'
        ref = _WRef('a', refs)

        # Setup storage and database we can use to test
        # the intricacies or our manual _p_changed manipulation
        from ZODB.DB import DB
        from ZODB.DemoStorage import DemoStorage
        import transaction
        db = DB(DemoStorage())
        self.addCleanup(db.close)
        conn = db.open()
        self.addCleanup(conn.close)

        internal = ContentBlobFile()
        internal.filename = u'ichigo'

        conn.root.key = internal
        transaction.commit()

        transaction.begin()

        # Setup our associations as if they were the old OOTreeSet
        assoc_set = OOTreeSet()
        assoc_set.add(ref)
        internal.__dict__['_associations'] = assoc_set

        # has_associations and count_associations still works.
        assert_that(internal.has_associations(),
                    is_(True))
        assert_that(internal.count_associations(),
                    is_(1))

        transaction.commit()
        transaction.begin()

        # Now simulate our existing ref has gone away
        # and add another association
        refs.pop('a')
        refs['b'] = 'B'
        internal.add_association(_WRef('b', refs))

        # Our dead ref is trimmed away
        assert_that(internal.count_associations(),
                    is_(1))
        assert_that(next(internal.associations()), is_('B'))

        # and our backing structure is a PersistentList
        assert_that(internal.__dict__['_associations'], instance_of(PersistentList))

        transaction.commit()

        transaction.begin()

        # Now force a cleanup that mutates associations
        refs.pop('b')
        internal.validate_associations()
        assert_that(internal.count_associations(),
                    is_(0))

        assert_that(internal._associations._p_changed, is_(True))

        # Force another one in the same transaction that doesn't do
        # anything.
        internal.validate_associations()
        assert_that(internal.count_associations(),
                    is_(0))

        # Note we didn't overwrite _p_changed=True
        assert_that(internal._associations._p_changed, is_(True))
        transaction.commit()

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
                                        has_entry('MimeType', 'application/vnd.nextthought.contentblobimage'))))

        assert_that(internal, has_property('__name__', is_('ichigo.gif')))
        internal.filename = u'foo'
        internal.name = u'ichigo.gif'
        assert_that(internal, has_property('__name__', is_('foo')))

        internal.reference = 'oid'
        interface.alsoProvides(internal, IInternalFileRef)
        blob = transform_to_blob(internal, associations=True)
        assert_that(blob, verifiably_provides(IContentBlobImage))
        assert_that(IInternalFileRef.providedBy(blob), is_(True))
        assert_that(blob, has_property('reference', is_('oid')))
        assert_that(blob, has_property('name', is_('ichigo.gif')))
        assert_that(blob, has_property('filename', is_('foo')))
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

        assert_that(internal, verifiably_provides(IS3File))
        assert_that(IContentTypeAware.providedBy(internal), is_(True))

        # value changed to URI
        assert_that(ext_obj, has_key('url'))
        assert_that(internal, has_property('contentType', 'image/gif'))
        assert_that(internal, has_property('filename', 'ichigo.gif'))
        assert_that(internal, has_property('name', 'ichigo.gif'))

        internal.invalidate()

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

        assert_that(internal, verifiably_provides(IS3Image))
        assert_that(IContentTypeAware.providedBy(internal), is_(True))

        # value changed to URI
        assert_that(ext_obj, has_key('url'))

        assert_that(internal, has_property('contentType', 'image/gif'))
        assert_that(internal, has_property('filename', 'ichigo.gif'))
        assert_that(internal, has_property('name', 'ichigo.gif'))
