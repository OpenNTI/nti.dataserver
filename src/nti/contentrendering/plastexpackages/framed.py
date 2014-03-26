# -*- coding: utf-8 -*-
"""
Partial support for the framed package. This is just enough 
to support Symmys. Support needs to be added for the following 
commands: oframed, shaded*, snugshade, snugshade*, leftbar, and
titled-frame. There are several 'expert' commands beyond these,
however the need to support them is open to discussion.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX import Environment

class framed(Environment):
	pass

class shaded(Environment):
	pass
