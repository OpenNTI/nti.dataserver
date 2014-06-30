#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Moved to nti.site.

$Id$
"""

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecated(
	"Moved to nti.site",
	_TrivialSite="nti.site.transient:TrivialSite",
	get_site_for_site_names="nti.site.site:get_site_for_site_names",
	synchronize_host_policies="nti.site.hostpolicy:synchronize_host_policies",
	run_job_in_all_host_sites="nti.site.hostpolicy:run_job_in_all_host_sites")
