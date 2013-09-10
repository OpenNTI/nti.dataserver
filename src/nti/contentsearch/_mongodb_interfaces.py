# -*- coding: utf-8 -*-
"""
MongoDB Search interfaces.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from dolmen.builtins import IDict

class IMongoDBObject(IDict):

	def toJSON():
		pass
