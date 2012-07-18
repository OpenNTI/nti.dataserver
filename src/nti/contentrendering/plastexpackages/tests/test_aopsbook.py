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
from nti.contentrendering.plastexpackages import aopsbook

def _simpleLatexDocument(maths):
    return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.aopsbook}',),
                                    bodies=maths )

def test_challProb():
    example = br"""
    \chall
    In Park School grade, 33 students and 12 teachers like none of these sports. \hints~\hint{cCount:3circles.1}, \hint{cCount:3circles.2} 
    """

    dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
    assert_that( dom.getElementsByTagName('hint'), has_length( 2 ) )
    
    #check that we don't have a comma in between hints
    hints = dom.getElementsByTagName('hint')
    assert_that(hints[0].nodeName, is_( hints[0].nextSibling.nodeName ))
    #Check if we don't have a trailing comma at the end.
    assert_that( dom.textContent, is_(" In Park School grade, 33 students and 12 teachers like none of these sports.  "))
    
def test_multipleTrailingComma():
    example = br"""
    \challhard
    Arbitrary content goes here. \hints~\hint{cCount:3circles.1},~\hint{cCount:3circles.2}, \hint{cCount:3circles.3} 
    """

    dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
    assert_that( dom.getElementsByTagName('hint'), has_length( 3 ) )
    
    #Check if we don't have a trailing comma at the end.
    assert_that( dom.textContent, is_(" Arbitrary content goes here.  "))
    
def test_oneHint():
    example = br"""
    \challhard
    Arbitrary content goes here. \hints~\hint{cCount:3circles.1}
    """
    dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
    assert_that( dom.getElementsByTagName('hint'), has_length( 1 ) )
    
    #Check if we don't have a trailing comma at the end.
    assert_that( dom.textContent, is_(" Arbitrary content goes here.  "))


