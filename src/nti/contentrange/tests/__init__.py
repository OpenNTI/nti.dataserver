#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals


import nti.testing.base

import nti.contentrange

class ConfiguringTestBase(nti.testing.base.SharedConfiguringTestBase):
	set_up_packages = (nti.contentrange,)
