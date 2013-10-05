#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" """
from __future__ import print_function, unicode_literals
import os
from hamcrest import assert_that, is_, has_length, contains_string
from hamcrest import has_property
from hamcrest import contains, has_item
from hamcrest import has_entry
import unittest

import anyjson as json

import plasTeX
from plasTeX.TeX import TeX


from nti.contentrendering.tests import buildDomFromString as _buildDomFromString
from nti.contentrendering.tests import simpleLatexDocumentText
from nti.contentrendering.tests import RenderContext

import nti.testing.base
from nti.externalization.tests import externalizes
from nti.testing.matchers import verifiably_provides

import nti.contentrendering
from nti.contentrendering.plastexpackages import graphics

def _simpleLatexDocument(maths):
    return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.graphics}',),
                                    bodies=maths )

def test_DeclareGraphicsRule():
    example = br"""
    \DeclareGraphicsRule{*}{mps}{*}{}
    """
    dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
    assert_that( dom.getElementsByTagName('DeclareGraphicsRule'), has_length( 1 ) )
