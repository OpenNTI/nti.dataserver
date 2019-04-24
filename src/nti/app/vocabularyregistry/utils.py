#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.site import registerUtility


def install_named_utility(utility, utility_name, provided, local_site_manager, component_named=None):
    # The install_utility from nti.site.localutility doesn't support named utility.
    if component_named is None:
        component_named = utility_name
    local_site_manager[utility_name] = utility
    registerUtility(local_site_manager,
                    utility,
                    provided=provided,
                    name=component_named)
