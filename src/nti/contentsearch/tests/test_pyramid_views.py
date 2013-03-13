#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.ntiids.ntiids import make_ntiid

from ..constants import invalid_type_
from ..pyramid_views import create_queryobject
from .. import interfaces as search_interfaces

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_)

class TestPyramidViews(ConfiguringTestBase):

	def test_create_query_object_accept(self):

		ntiid = make_ntiid(nttype='hollow', specific='vastolorde')
		matchdict = {'term':'menos', 'ntiid':ntiid}
		params = {'accept':'application/vnd.nextthought.personalblogentrypost,application/vnd.nextthought.note',
				  'batchSize':'10', 'batchStart':'0'}

		qo = create_queryobject('harribel@bleach.com', params, matchdict)
		assert_that(search_interfaces.ISearchQuery.providedBy(qo), is_(True))
		assert_that(qo.username, is_('harribel@bleach.com'))
		assert_that(qo.term, is_('menos'))
		assert_that(qo.location, is_(ntiid))
		assert_that(qo.batchSize, is_(10))
		assert_that(qo.batchStart, is_(0))
		assert_that(qo.searchOn, is_((u'note', u'post')))

		params = {'accept':'application/vnd.nextthought.foo'}
		qo = create_queryobject('harribel@bleach.com', params, matchdict)
		assert_that(qo.searchOn, is_((invalid_type_,)))

	def test_create_query_object_exclude(self):

		ntiid = make_ntiid(nttype='hollow', specific='vastolorde')
		matchdict = {'term':'arrancar', 'ntiid':ntiid}
		params = {'exclude':'application/vnd.nextthought.personalblogentrypost,application/vnd.nextthought.note',
				  'batchSize':'100', 'batchStart':'3'}

		qo = create_queryobject('ulquiorra@bleach.com', params, matchdict)
		assert_that(search_interfaces.ISearchQuery.providedBy(qo), is_(True))
		assert_that(qo.username, is_('ulquiorra@bleach.com'))
		assert_that(qo.term, is_('arrancar'))
		assert_that(qo.location, is_(ntiid))
		assert_that(qo.batchSize, is_(100))
		assert_that(qo.batchStart, is_(3))
		assert_that(qo.searchOn, is_((u'content', u'highlight', u'messageinfo', u'redaction')))

		params = {'exclude':'*/*'}
		qo = create_queryobject('ulquiorra@bleach.com', params, matchdict)
		assert_that(qo.searchOn, is_((invalid_type_,)))

	def test_create_query_object_badnumbers(self):

		ntiid = make_ntiid(nttype='hollow', specific='vastolorde')
		matchdict = {'term':'arrancar', 'ntiid':ntiid}
		params = {'batchSize':'-100', 'batchStart':'3'}

		try:
			create_queryobject('ulquiorra@bleach.com', params, matchdict)
			self.fail()
		except:
			pass

		params = {'batchSize':'100', 'batchStart':'-3'}
		try:
			create_queryobject('ulquiorra@bleach.com', params, matchdict)
			self.fail()
		except:
			pass

		params = {'batchSize':'xx', 'batchStart':'-3'}
		try:
			create_queryobject('ulquiorra@bleach.com', params, matchdict)
			self.fail()
		except:
			pass

