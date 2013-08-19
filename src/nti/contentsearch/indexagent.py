#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
External index agent funnction

$Id: _indexagent.py 17623 2013-03-27 17:28:52Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import _indexagent

def handle_external(entity, changeType, oid, broadcast=None):
	return _indexagent.handle_external(entity, changeType, oid, broadcast)
