#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

from nti.testing.matchers import is_empty

from zope import interface

from ZODB.interfaces import IBroken

from nti.dataserver import contenttypes
from nti.dataserver import interfaces as nti_interfaces

from nti.coremetadata.mixins import ZContainedMixin

from nti.datastructures.datastructures import ContainedStorage

from nti.dublincore.datastructures import CreatedModDateTrackingObject

from nti.externalization.oids import toExternalOID
from nti.externalization.oids import to_external_ntiid_oid

from nti.ntiids import ntiids

import nti.dataserver.tests.mock_dataserver as mock_dataserver

from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

class TestContainedStorage(DataserverLayerTest):

	class C(CreatedModDateTrackingObject, ZContainedMixin):
		def to_container_key(self):
			return to_external_ntiid_oid(self, default_oid=str(id(self)))

	@WithMockDS
	def test_volatile_attributes(self):

		with mock_dataserver.mock_db_trans(self.ds):
			cs = ContainedStorage()
			self.ds.root['key'] = cs

			assert_that(cs._p_jar, has_property('_registered_objects',
												has_item(cs)))
			assert_that(cs._p_jar, has_property('_added',
												has_entry(cs._p_oid, cs)))

		with mock_dataserver.mock_db_trans(self.ds):
			cs = self.ds.root['key']
			assert_that(cs, has_property('_p_changed', none()))

			cs.afterAddContainedObject = lambda *args: None
			cs.afterGetContainedObject = lambda *args: None
			cs.afterDeleteContainedObject = lambda *args: None

			assert_that(cs, has_property('_p_changed', False))

			assert_that(cs._p_jar, has_property('_registered_objects',
												does_not(has_item(cs))))
			assert_that(cs._p_jar, has_property('_added',
												is_empty()))

	@WithMockDSTrans
	def test_id_is_ntiid(self):
		cs = ContainedStorage()
		mock_dataserver.current_transaction.add(cs)

		obj = contenttypes.Note()
		obj.containerId = 'foo'
		cs.addContainedObject(obj)

		assert_that(obj._p_jar, is_(cs._p_jar))
		assert_that(obj._p_jar, is_(not_none()))
		ntiids.validate_ntiid_string(obj.id)

		# Without a creator, we get the system principal as the provider
		ntiid = ntiids.get_parts(obj.id)
		assert_that(ntiid.provider, is_(nti_interfaces.SYSTEM_USER_NAME))
		assert_that(ntiid.nttype, is_('OID'))
		assert_that(ntiid.specific, is_(toExternalOID(obj)))

		# with a creator, we get the creator as the provider
		cs = ContainedStorage(create='sjohnson@nextthought.com')
		mock_dataserver.current_transaction.add(cs)

		obj = contenttypes.Note()
		obj.containerId = 'foo'
		cs.addContainedObject(obj)
		assert_that(obj._p_jar, is_(cs._p_jar))
		assert_that(obj._p_jar, is_(not_none()))
		ntiids.validate_ntiid_string(obj.id)

		ntiid = ntiids.get_parts(obj.id)
		assert_that(ntiid.provider, is_('sjohnson@nextthought.com'))
		assert_that(ntiid.nttype, is_(ntiids.TYPE_OID))
		assert_that(ntiid.specific, is_(toExternalOID(obj)))

	@WithMockDSTrans
	def test_cleanup(self):
		cs = ContainedStorage()
		mock_dataserver.current_transaction.add(cs)

		obj = contenttypes.Note()
		obj.containerId = 'foo'
		cs.addContainedObject(obj)
		container = cs.getContainer('foo')
		assert_that(container, has_length(1))

		interface.alsoProvides(obj, IBroken)

		removed = cs.cleanBroken()
		assert_that(removed, is_(1))
		assert_that(container, has_length(0))
