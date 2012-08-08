#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import nti.contentfragments
import nti.contentfragments.interfaces
from zope import component

import nti.tests
from hamcrest import assert_that
from hamcrest import is_

setUpModule = lambda: nti.tests.module_setup( set_up_packages=(nti.contentfragments,) )

def test_defaults():
	scanner = component.getUtility( nti.contentfragments.interfaces.ICensoredContentScanner )
	strat = component.getUtility( nti.contentfragments.interfaces.ICensoredContentStrategy )

	bad_val = 'Guvf vf shpxvat fghcvq, lbh ZbgureShpxre onfgneq'.encode( 'rot13' )

	assert_that( strat.censor( bad_val, scanner.scan( bad_val ) ),
				 is_( 'This is ******* stupid, you ************ *******' ) )
