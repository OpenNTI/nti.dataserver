# -*- coding: utf-8 -*-
"""
Spambayes module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import math

from zope import component

from nti.contentsearch.spambayes import interfaces as sps_interfaces

LN2 = math.log(2)

default_hist_nbuckets = 200
default_hist_percentiles = (5, 25, 75, 95)

PERSISTENT_HAM_INT = 1
PERSISTENT_SPAM_INT = 2
PERSISTENT_UNSURE_INT = 0

def is_spam(disposition):
	return disposition == PERSISTENT_SPAM_INT

def is_ham(disposition):
	return disposition == PERSISTENT_HAM_INT

def is_unsure(disposition=None):
	return disposition is None or disposition == PERSISTENT_UNSURE_INT

def classify(prob):
	return component.getUtility(sps_interfaces.IProbabilityClassifier)(prob)
