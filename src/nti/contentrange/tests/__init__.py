#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals


import nti.tests

import nti.contentrange

class ConfiguringTestBase(nti.tests.SharedConfiguringTestBase):
	set_up_packages = (nti.contentrange,)
