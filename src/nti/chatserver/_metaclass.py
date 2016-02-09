#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Metaclasses to make sending chat events easy.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
from collections import Iterable

from zope import component

from nti.chatserver.interfaces import IChatserver

def _send_event(chatserver, names, evt_name, *args):
	"""
	Utility method to send an event to a username or usernames.
	"""
	if isinstance(names, six.string_types) or not isinstance(names, Iterable):
		names = (names,)
	for sname in names:
		chatserver.send_event_to_user(sname, evt_name, *args)

def _chatserver(s=None):
	return getattr(s, '_chatserver', None) or component.queryUtility(IChatserver)

class _ChatObjectMeta(type):

	def __new__(cls, clsname, clsbases, clsdict):

		if '__emits__' not in clsdict:
			return type.__new__(cls, clsname, clsbases, clsdict)

		def make_emit(signal):
			return lambda s, sessions, *args: _send_event(_chatserver(s),
														   sessions,
														   signal,
														   *args)
		for signal in (clsdict['__emits__']):
			name = signal if '_' in signal else 'chat_' + signal
			clsdict['emit_' + signal] = make_emit(name)

		return type.__new__(cls, clsname, clsbases, clsdict)
