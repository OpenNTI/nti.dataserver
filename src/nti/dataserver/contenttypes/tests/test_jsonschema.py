#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.coremetadata.jsonschema import make_schema

from nti.dataserver.interfaces import INote

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

class TestJsonSchema(DataserverLayerTest):

	def test_note(self):
		result = make_schema(INote)
		import pprint
		pprint.pprint(result)
	