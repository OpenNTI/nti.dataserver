#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that

from nti.testing.matchers import verifiably_provides

from nti.contentrange.contentrange import DomContentPointer

from nti.contentrange.interfaces import ITimeContentPointer
from nti.contentrange.interfaces import ITimeRangeDescription
from nti.contentrange.interfaces import ITranscriptContentPointer
from nti.contentrange.interfaces import ITranscriptRangeDescription

from nti.contentrange.tests import ConfiguringTestBase

from nti.contentrange.timeline import TimeContentPointer
from nti.contentrange.timeline import TimeRangeDescription
from nti.contentrange.timeline import TranscriptContentPointer
from nti.contentrange.timeline import TranscriptRangeDescription

from nti.externalization.externalization import toExternalObject

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object


class TestTimeLineRange(ConfiguringTestBase):

    def verify(self, clazz, iface, kwargs):
        assert_that(clazz(**kwargs), verifiably_provides(iface))
        assert_that(update_from_external_object(clazz(),
                                                toExternalObject(clazz(**kwargs)), require_updater=True),
                    is_(clazz(**kwargs)))

    def test_default_verifies_externalization(self):
        self.verify(TimeContentPointer, ITimeContentPointer,
                    {
                        'role': u"start",
                        'seconds': 1
                    })

        self.verify(TimeRangeDescription, ITimeRangeDescription,
                    {
                        'seriesId': u"myseries",
                        'start': TimeContentPointer(role=u'start', seconds=1),
                        'end': TimeContentPointer(role=u'end', seconds=2)
                    })

        self.verify(TranscriptContentPointer, ITranscriptContentPointer,
                    {
                        'role': u"start",
                        'seconds': 1,
                        'pointer': DomContentPointer(elementId=u'foo', role=u'start', elementTagName=u'p'),
                        'cueid': u'myid'
                    })

        self.verify(TranscriptRangeDescription, ITranscriptRangeDescription,
                    {
                        'seriesId': u"myseries",
                        'start': TranscriptContentPointer(role=u"start", seconds=1, cueid=u'myid',
                                                          pointer=DomContentPointer(elementId=u'foo',
                                                                                    role=u'start',
                                                                                    elementTagName=u'p')),
                        'end': TranscriptContentPointer(role=u"end", seconds=1, cueid=u'umyid',
                                                        pointer=DomContentPointer(elementId=u'foo',
                                                                                  role=u'end',
                                                                                  elementTagName=u'p'))})

    def test_external_legacy_factory(self):
        for name in ('TimeRangeDescription', 'TimeContentPointer',
                     'TranscriptContentPointer', 'TranscriptRangeDescription'):
            ext_obj = {"Class": name}
            factory = find_factory_for(ext_obj)
            assert_that(factory, is_not(none()))
