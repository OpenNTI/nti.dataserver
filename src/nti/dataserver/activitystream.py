#!/usr/bin/env python2.7

"""
Functions and architecture for general activity streams.
"""

from nti.dataserver import interfaces as nti_interfaces
from zope import component

def enqueue_change( change, **kwargs ):
	ds = component.queryUtility( nti_interfaces.IDataserver )
	if ds:
		ds.enqueue_change( change, **kwargs )
