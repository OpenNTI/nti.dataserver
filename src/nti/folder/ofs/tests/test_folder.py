#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from zope.interface.verify import verifyClass

from nti.folder.ofs.folder import Folder
from nti.folder.ofs.interfaces import IFolder

from nti.folder.tests import SharedConfiguringTestLayer

class TestFolder(unittest.TestCase):

	layer = SharedConfiguringTestLayer
	
	def test_interfaces(self):
		verifyClass(IFolder, Folder)
