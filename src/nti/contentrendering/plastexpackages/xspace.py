# -*- coding: utf-8 -*-
"""
Partial support for the xspace package. This is just enough 
to support parsing, however this command does semi-complicated 
whitespace manipulation that will require careful work on the render templates 
to do correctly.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX import Command

class xspace(Command):
	pass

