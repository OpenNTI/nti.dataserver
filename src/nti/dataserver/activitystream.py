#!/usr/bin/env python2.7

"""
Functions and architecture for general activity streams.
"""

import logging
logger = logging.getLogger(__name__)

import os
from nti.dataserver import interfaces as nti_interfaces
from nti.chatserver import interfaces as chat_interfaces
from zope import component

def enqueue_change( change, **kwargs ):
	ds = component.queryUtility( nti_interfaces.IDataserver )
	if ds:
		ds.enqueue_change( change, **kwargs )
