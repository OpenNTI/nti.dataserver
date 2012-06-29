#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope.traversing import interfaces as trv_interfaces, api as trv_api

from pyramid.testing import DummyRequest

from nti.appserver import traversal

def test_unicode_traversal():

	@interface.implementer(trv_interfaces.ITraversable)
	class BrokenTraversable(object):
		raised = False
		def traverse( self, name, furtherPath ):
			BrokenTraversable.raised = True
			getattr( self, u'\u2019', None ) # Raise unicode error

	@interface.implementer(trv_interfaces.ITraversable)
	class DirectTraversable(object):
		def traverse( self, name, furtherPath ):
			return BrokenTraversable()

	req = DummyRequest(path='/a/b/c')
	req.environ['bfg.routes.matchdict'] = {'traverse': ('a','b','c')}
	traversal.ZopeResourceTreeTraverser( DirectTraversable() )( req )
	assert BrokenTraversable.raised
