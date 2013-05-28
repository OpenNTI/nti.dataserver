# -*- coding: utf-8 -*-
"""
Content search generation installation.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

generation = 27

from zope.generations.generations import SchemaManager

class _ContentSearchSchemaManager(SchemaManager):
	"""
	A schema manager that we can register as a utility in ZCML.
	"""
	def __init__(self):
		super(_ContentSearchSchemaManager, self).__init__(generation=generation,
														  minimum_generation=generation,
														  package_name='nti.contentsearch.generations')

def evolve(context):
	pass
