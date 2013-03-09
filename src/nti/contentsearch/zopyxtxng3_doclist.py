# -*- coding: utf-8 -*-
"""
Zopyx override for DocidList.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from BTrees.LLBTree import LLTreeSet

DocidList = LLTreeSet
