# -*- coding: utf-8 -*-
"""
MongoDB Search interfaces.

$Id: _cloudsearch_interfaces.py 17836 2013-04-02 17:22:04Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from dolmen.builtins import IDict

class IMongoDBObject(IDict):

	def toJSON():
		pass
