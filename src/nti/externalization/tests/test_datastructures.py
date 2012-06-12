#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import sys

from zope import interface

from ..datastructures import ModuleScopedInterfaceObjectIO

from hamcrest import assert_that, has_property
from nose.tools import assert_raises

def test_finding_linear_interface():

	class IRoot(interface.Interface): pass
	class IChild(IRoot): pass
	class IGrandChild(IChild): pass

	class ISister(IRoot): pass

	@interface.implementer(IGrandChild,ISister)
	class Inconsistent(object): pass

	mod = sys.modules[__name__]

	class IO(ModuleScopedInterfaceObjectIO):
		_ext_search_module = mod

	with assert_raises( TypeError ):
		IO( Inconsistent() )


	@interface.implementer(ISister)
	class Sister(object): pass

	@interface.implementer(IGrandChild)
	class InconsistentGrandChild(Sister): pass

	with assert_raises( TypeError ):
		IO( InconsistentGrandChild() )

	@interface.implementer(IGrandChild)
	class Consistent(object): pass

	io = IO( Consistent() )
	assert_that( io, has_property( '_iface', IGrandChild ) )
