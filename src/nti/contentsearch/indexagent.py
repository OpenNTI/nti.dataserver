#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
External index agent functions

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import _indexagent

def handle_external(entity, changeType, oid, broadcast=None):
	return _indexagent.handle_external(entity, changeType, oid, broadcast)
