#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Monkey-patch for ZLibStorage and RelStorage to work correctly together.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

def _patch_zlibstorage_for_IMVCCStorage():
	try:
		from zc.zlibstorage import ZlibStorage
	except ImportError:
		return

	if 'new_instance' not in ZlibStorage.__dict__:
		# ZLibStorage claims to provide the same
		# interfaces as whatever it is wrapping.
		# It also passes through any methods it does not implement
		# to the storage it is wrapping.
		# If the storage it is wrapping implements IMVCCStorage, then
		# the wrapping storage provides a 'new_instance' method and
		# ZLibStorage happily claims to provide the same and passes that
		# method call through. When a transaction begins and an isolated storage
		# instance is needed, then, ZLibStorage gets dropped and we lose all
		# compression.
		# The only known implementation if IMVCCStorage is RelStorage,
		# so might as well fix that here.
		# (Sigh, this means all our databases are currently uncompressed)
		# see https://mail.zope.org/pipermail/zodb-dev/2013-March/014965.html
		def new_instance(self):
			new_self = type(self).__new__(type(self))
			new_self.__dict__ = self.__dict__.copy()
			new_self.base = self.base.new_instance()
			# Because these are bound methods, we must re-copy them or ivars might be wrong, like _transaction
			for name in self.copied_methods:
				v = getattr(new_self.base, name, None)
				if v is not None:
					setattr(new_self, name, v)
			return new_self
		ZlibStorage.new_instance = new_instance

_patch_zlibstorage_for_IMVCCStorage()

def patch():
	pass
