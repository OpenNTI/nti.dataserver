#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry

from nti.tests import validly_provides

from nti.contentprocessing import metadata_extractors, interfaces

import os.path
from rdflib import Graph

def test_metadata_provides():

	metadata = metadata_extractors.ContentMetadata()
	assert_that( metadata, validly_provides( interfaces.IContentMetadata ) )

def test_rdflib_can_parse_file():
	the_file = os.path.abspath( os.path.join( os.path.dirname(__file__),
											  'og_metadata.html') )

	graph = Graph()
	graph.parse( the_file, format='rdfa' )
