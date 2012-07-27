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

import nti.tests
from nti.externalization.tests import externalizes
from nti.tests import verifiably_provides

import nti.contentrendering
from nti.contentrendering.plastexpackages import picins
from nti.contentrendering.plastexpackages import graphicx

def _simpleLatexDocument(maths):
    return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.picins}',),
                                    bodies=maths )

def test_picskip():
    example = br"""
    \picskip{0}
    """
    dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
    assert_that( dom.getElementsByTagName('picskip'), has_length( 0 ) )

def test_parpic():
    example = br"""
    \parpic(0pt,2.8in)[r][t]{\includegraphics{test}}
    """
    dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
    assert_that( dom.getElementsByTagName('parpic'), has_length( 1 ) )
