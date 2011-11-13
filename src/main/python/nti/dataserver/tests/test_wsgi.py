#!/usr/bin/env python2.7

import os
import sys
try:
	import plasTeX
except ImportError:
	toAdd = "../../../../../../../../AoPS/src/main/plastex"
	if os.path.dirname( __file__ ):
		toAdd = os.path.abspath( os.path.join( os.path.dirname( __file__ ), toAdd ) )

	sys.path.append( toAdd )
	import plasTeX
	assert plasTeX

from hamcrest import (assert_that, is_, has_entry, instance_of,
					  has_key, is_in, not_none, is_not, greater_than,
					  same_instance)
import unittest

import UserDict
import collections

import persistent
import json
import plistlib
from nti.dataserver.datastructures import (getPersistentState, toExternalOID, toExternalObject,
									   ExternalizableDictionaryMixin, CaseInsensitiveModDateTrackingOOBTree,
									   LastModifiedCopyingUserList, PersistentExternalizableWeakList,
									   ContainedStorage, ContainedMixin, CreatedModDateTrackingObject,
									   to_external_representation, EXT_FORMAT_JSON, EXT_FORMAT_PLIST)
from nti.dataserver.wsgi import LibraryGet
import nti.dataserver.library

class TestLibraryGet(unittest.TestCase):

	def test_get( self ):
		library = nti.dataserver.library.Library( (('/Library/Foo', True),) )

		get = LibraryGet( library )
		def sr( *args ): pass
		bdy = get( {'PATH_INFO': ''}, sr )
		assert_that( bdy, not_none() )


if __name__ == '__main__':
	unittest.main()
