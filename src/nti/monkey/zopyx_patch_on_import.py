#!/usr/bin/env python

from __future__ import print_function, unicode_literals, absolute_import

__docformat__ = "restructuredtext en"

import sys

from nti.contentsearch import zopyxtxng3corelogger
sys.modules["zopyx.txng3.core.logger"] = zopyxtxng3corelogger

from zopyx.txng3.core import index as zopycoreidx
from zopyx.txng3.core import evaluator as zopyevaluator

from nti.contentsearch import zopyxtxng3coreresultset as ntizopyrs

for module in (zopycoreidx, zopyevaluator):
	module.unionResultSets = ntizopyrs.unionResultSets
	module.inverseResultSet = ntizopyrs.inverseResultSet
	module.intersectionResultSets = ntizopyrs.intersectionResultSets