# -*- coding: utf-8 -*-
"""
Payment interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

class IRegisterPurchaseData(interface.Interface):
	username = interface.Attribute("The registering username")
	purchase_id = interface.Attribute("The purchase identifier")

class RegisterPurchaseData(object):

	def __init__( self, purchase_id, username):
		self.username = username
		self.purchase_id = purchase_id
