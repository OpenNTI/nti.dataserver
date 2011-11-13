#!/usr/bin/env python2.7

"""
Functions and architecture for general activity streams.
"""

from _Dataserver import Dataserver

def enqueue_change( change, **kwargs ):
	ds = Dataserver.get_shared_dataserver()
	if ds:
		ds.enqueue_change( change, **kwargs )
