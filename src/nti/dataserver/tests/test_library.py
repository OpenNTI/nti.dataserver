#!/usr/bin/env python2.7

from hamcrest import (assert_that, is_, has_entry, instance_of,
					  has_key, is_in, not_none, is_not, greater_than,
					  same_instance)
import unittest

from nti.dataserver.datastructures import (getPersistentState, toExternalOID, toExternalObject,
									   ExternalizableDictionaryMixin, CaseInsensitiveModDateTrackingOOBTree,
									   LastModifiedCopyingUserList, PersistentExternalizableWeakList,
									   ContainedStorage, ContainedMixin, CreatedModDateTrackingObject,
									   to_external_representation, EXT_FORMAT_JSON, EXT_FORMAT_PLIST)

import nti.dataserver.library

class TestLibrary( unittest.TestCase ):

	def test_space_in_path( self ):

		library = nti.dataserver.library.Library( (('/Library/Foo With Spaces', True),) )
		ent = library.titles[0]
		assert_that( ent.root, is_( '/Foo%20With%20Spaces/' ) )
		assert_that( ent.icon, is_( '/Foo%20With%20Spaces/icons/Foo%20With%20Spaces-Icon.png' ) )



if __name__ == '__main__':
	unittest.main()
