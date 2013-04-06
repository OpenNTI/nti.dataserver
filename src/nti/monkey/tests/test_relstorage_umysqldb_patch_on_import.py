#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry

import nti.tests

def test_timestamp_to_tid_patch():
	import nti.monkey.relstorage_umysqldb_patch_on_import
	nti.monkey.relstorage_umysqldb_patch_on_import.patch()

	from relstorage.storage import RelStorage

	class Adapter(object):
		pass

	class Schema(object):
		def prepare(self): pass

	class Locker(object):
		def hold_commit_lock( self, cursor, ensure_current=True ):
			pass

	class TxnControl(object):
		last_tid = 1
		def get_tid( self, cursor ):
			return self.last_tid
		def add_transaction( self, cursor, tid_int, user, desc, ext ):
			pass

	adapter = Adapter()
	adapter.schema = Schema()
	adapter.txncontrol = TxnControl()
	adapter.locker = Locker()

	storage = RelStorage( adapter )
	storage._transaction = object()
	storage._ude = (None, None, None)

	storage._prepare_tid()

	assert_that( storage._tid, is_( bytes ) ) # bytes, not unicode
