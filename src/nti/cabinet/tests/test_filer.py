#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import ends_with
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import starts_with
from hamcrest import greater_than
from hamcrest import has_property
does_not = is_not

from nti.testing.matchers import validly_provides
from nti.testing.matchers import verifiably_provides

import shutil
import tempfile
import unittest

from six import StringIO

from nti.base.interfaces import DEFAULT_CONTENT_TYPE

from nti.cabinet.filer import DirectoryFiler

from nti.cabinet.interfaces import ISource
from nti.cabinet.interfaces import ISourceBucket

from nti.cabinet.tests import SharedConfiguringTestLayer


class TestFiler(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    dir_name = u'bleach manga'

    def get_data_source(self):
        return StringIO("<ichigo/>")

    def test_operations(self):
        tmp_dir = tempfile.mkdtemp(dir="/tmp")
        try:
            filer = DirectoryFiler(tmp_dir)
            data = self.get_data_source()
            href = filer.save(u"ichigo.xml", data, relative=False,
                              contentType=u"application/xml", overwrite=True)
            assert_that(href, is_not(none()))
            assert_that(href, starts_with(tmp_dir))
            assert_that(filer.contains(href), is_(True))

            source = filer.get(href)
            assert_that(source, is_not(none()))
            assert_that(source, validly_provides(ISource))
            assert_that(source, verifiably_provides(ISource))
            assert_that(source, has_property('length', is_(9)))
            assert_that(source, has_property('name', is_("ichigo.xml")))
            assert_that(source, has_property('path', is_(tmp_dir)))

            assert_that(source,
                        has_property('__parent__', is_not(none())))

            assert_that(source,
                        has_property('createdTime', greater_than(0)))

            assert_that(source,
                        has_property('lastModified', greater_than(0)))

            assert_that(source,
                        has_property('filename', ends_with("/ichigo.xml")))

            assert_that(source, has_property('contentType', ends_with("xml")))

            assert_that(source.read(), is_("<ichigo/>"))
            source.close()

            source = filer.get(href)
            source.data = b'aizen and ichigo'
            assert_that(source.read(5), is_(b'aizen'))
            source.close()

            source = filer.get("/home/foo")
            assert_that(source, is_(none()))

            data = self.get_data_source()
            href = filer.save(u"ichigo.xml",
                              data,
                              contentType=u"text/xml",
                              overwrite=False)
            assert_that(href, does_not(ends_with("ichigo.xml")))

            data = self.get_data_source()
            href = filer.save(u"ichigo.xml",
                              data,
                              bucket=self.dir_name,
                              contentType=u"text/xml",
                              overwrite=True)
            assert_that(href,
                        ends_with("%s/ichigo.xml" % self.dir_name))

            assert_that(filer.is_bucket(self.dir_name),
                        is_(True))

            assert_that(filer.list(self.dir_name),
                        has_length(greater_than(0)))

            assert_that(filer.contains(href),
                        is_(True))

            assert_that(filer.contains("ichigo.xml", self.dir_name),
                        is_(True))

            # check parent
            ichigo = filer.get(href)
            assert_that(ichigo,
                        has_property('path', is_(tmp_dir + '/' + self.dir_name)))
            bucket = ichigo.__parent__
            assert_that(bucket,
                        has_property('__name__', is_(self.dir_name)))
            assert_that(bucket,
                        has_property('__parent__', is_(none())))
            assert_that(bucket,
                        has_property('filer', is_(filer)))

            # check getting a bucket
            bucket = filer.get(self.dir_name)
            assert_that(bucket, has_property('bucket', is_(self.dir_name)))
            assert_that(bucket, verifiably_provides(ISourceBucket))
            assert_that(bucket, has_property('__parent__', is_not(none())))
            ichigo = bucket.getChildNamed("ichigo.xml")
            assert_that(ichigo, is_not(none()))

            listed = bucket.enumerateChildren()
            assert_that(listed, is_(['%s/ichigo.xml' % self.dir_name]))

            foo = bucket.getChildNamed("foo.xml")
            assert_that(foo, is_(none()))

            data = self.get_data_source()
            href = filer.save(u"ichigo.xml",
                              data,
                              bucket=u"%s/souls" % self.dir_name,
                              contentType=u"text/xml",
                              overwrite=True)
            assert_that(href,
                        ends_with("%s/souls/ichigo.xml" % self.dir_name))

            assert_that(filer.contains(href), is_(True))
            assert_that(filer.contains("ichigo.xml", "%s/souls" % self.dir_name),
                        is_(True))

            listed = filer.list(self.dir_name)
            assert_that(listed,
                        is_(['%s/ichigo.xml' % self.dir_name, '%s/souls' % self.dir_name]))

            assert_that(filer.is_bucket('%s/souls' % self.dir_name),
                        is_(True))

            assert_that(filer.is_bucket('%s/ichigo.xml' % self.dir_name),
                        is_(False))

            assert_that(filer.remove(href), is_(True))
            source = filer.get(href)
            assert_that(source, is_(none()))
            assert_that(filer.contains(href), is_(False))

            # No type
            href = filer.save(u"ichigo",
                              data,
                              bucket=u"%s/souls/missing_type" % self.dir_name,
                              overwrite=True)
            assert_that(href,
                        ends_with("%s/souls/missing_type/ichigo" % self.dir_name))

            assert_that(filer.contains(href), is_(True))
            assert_that(filer.contains("ichigo", "%s/souls/missing_type" % self.dir_name),
                        is_(True))

            bleh = filer.get(href)
            assert_that(bleh, is_(not_none()))
            assert_that(bleh,
                        has_property('contentType', is_(DEFAULT_CONTENT_TYPE)))

            # test no effect
            bleh.createdTime = bleh.lastModified = 0
            assert_that(bleh,
                        has_property('createdTime', greater_than(0)))

            assert_that(bleh,
                        has_property('lastModified', greater_than(0)))

            assert_that(filer.remove(href), is_(True))
            source = filer.get(href)
            assert_that(source, is_(none()))
            assert_that(filer.contains(href), is_(False))
        finally:
            shutil.rmtree(tmp_dir, True)
