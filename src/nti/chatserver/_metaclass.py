#!/usr/bin/env python
""" Metaclasses to make sending chat events easy. """
from __future__ import print_function, unicode_literals
__docformat__ = "restructuredtext en"

import logging
logger = logging.getLogger( __name__ )

import collections
import six

from zope import component

from . import interfaces

def _send_event( chatserver, names, evt_name, *args ):
	"""
	Utility method to send an event to a username or usernames.
	"""
	if isinstance(names, six.string_types) or not isinstance( names, collections.Iterable ):
		names = (names,)
	for sname in names:
		chatserver.send_event_to_user( sname, evt_name, *args )

class _ChatObjectMeta(type):

	def __new__( mcs, clsname, clsbases, clsdict ):
		if '__emits__' not in clsdict:
			return type.__new__( mcs, clsname, clsbases, clsdict )

		def make_emit(signal):
			return lambda s, sessions, *args: _send_event( getattr(s, '_chatserver', None) or component.queryUtility( interfaces.IChatserver ),
														   sessions,
														   signal,
														   *args )
		for signal in (clsdict['__emits__']):
			clsdict['emit_' + signal] = make_emit( signal if '_' in signal else 'chat_' + signal )

		return type.__new__( mcs, clsname, clsbases, clsdict )
