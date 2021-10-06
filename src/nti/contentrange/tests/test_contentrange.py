#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import has_length
from hamcrest import has_property
from hamcrest import assert_that
from hamcrest import less_than_or_equal_to

from nti.testing.matchers import verifiably_provides

from zope import interface

from zope.schema import interfaces as sch_interfaces

from nti.contentrange import timeline
from nti.contentrange import interfaces
from nti.contentrange import contentrange

from nti.contentrange.tests import ConfiguringTestBase

from nti.externalization.externalization import toExternalObject

from nti.externalization import update_from_external_object

from nti.externalization.tests import externalizes


class TestContentRange(ConfiguringTestBase):

    def test_default_verifies_externalization(self):
        # Constructing new objects of all the interface types
        # implement the interface they claim.
        # The can also be externalized.

        kwargs = {
            'start': contentrange.DomContentPointer(elementId=u'foo', 
                                                    role=u'start', 
                                                    elementTagName=u'p'),
            'end': contentrange.DomContentPointer(elementId=u'foo', 
                                                  role=u'end', 
                                                  elementTagName=u'p'),
            'ancestor': contentrange.ElementDomContentPointer(elementId=u'foo', 
                                                              role=u'end',
                                                              elementTagName=u'p'),
            'elementId': u'baz', 'elementTagName': u'div', 'role': u'start',
            'contextText': u'word', u'contextOffset': 4,
            'edgeOffset': 9, 'contexts': [contentrange.TextContext(contextText=u'foo')]
        }

        seen_ifaces = set()
        for x in contentrange.__dict__.values():
            if type(x) == type:
                for iface in interface.implementedBy(x):
                    if iface.__module__ != interfaces.__name__:
                        continue

                    seen_ifaces.add(x)
                    assert_that(x(**kwargs), verifiably_provides(iface))
                    assert_that(x(**kwargs), externalizes())

                    # MimeType is added by an external decorator we don't have at this layer
                    # assert_that( toExternalObject( x() ), has_key( 'MimeType' ) )
                    assert_that(update_from_external_object(x(),
                                                            toExternalObject(x(**kwargs)),
                                                            require_updater=True),
                                is_(x(**kwargs)))

        # We did find implementations of all the interfaces
        expected_count = 0
        for x in interfaces.__dict__.values():
            if type(x) == interface.interface.InterfaceClass:
                expected_count += 1

        assert_that(seen_ifaces, has_length(
            less_than_or_equal_to(expected_count)))

    def test_external_validation(self):
        edc = contentrange.ElementDomContentPointer()
        with self.assertRaises(sch_interfaces.RequiredMissing):
            # The 'role' attribute is missing and should be required
            update_from_external_object(edc, {'elementId': u'baz', 'elementTagName': u'div'},
                                        require_updater=True)

        with self.assertRaises(sch_interfaces.ConstraintNotSatisfied):
            # A role value outside the schema
            update_from_external_object(edc, {'role': u'unknown'},
                                        require_updater=True)

        with self.assertRaises(sch_interfaces.TooShort):
            # Too short an elementId
            update_from_external_object(edc, {'elementId': u''}, 
                                        require_updater=True)

        with self.assertRaises(sch_interfaces.TooShort):
            # Too short an elementTagName
            update_from_external_object(edc, {'elementTagName': u''},
                                        require_updater=True)

        tdc = contentrange.TextDomContentPointer()
        tdc.ancestor = edc
        with self.assertRaises(sch_interfaces.TooSmall):
            update_from_external_object(tdc, {'edgeOffset': -1})

        with self.assertRaises(sch_interfaces.TooShort):
            update_from_external_object(tdc, {'contexts': []})

        time_pointer = timeline.TimeContentPointer()
        with self.assertRaises(sch_interfaces.WrongType) as ex:
            update_from_external_object(time_pointer,
                                        {'seconds': 1.1, 'role': u'start'})

        ex = ex.exception
        assert_that(ex,
                    has_property('field', interfaces.ITimeContentPointer['seconds']))
