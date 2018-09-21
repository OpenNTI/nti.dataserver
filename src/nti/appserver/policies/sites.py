#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Component registries and site managers for specific sites.

These use :mod:`z3c.baseregistry` to be configurable using ZCML. Thus,
for each constant declared here, there is a corresponding ZCML file
that registers the constant as a utility with a matching name. Any configuration
for that site belongs in a ``registerIn`` directive within that ZCML file. These
files then have to be referenced from the main configuration file.

When creating a site manager, you *MUST* use :const:`BASEADULT` or :const:`MATHCOUNTS`
in its base chain. You do not (should not) create the site object
in this module.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from z3c.baseregistry.baseregistry import BaseComponents

# Eventually we probably want these to use the main Dataserver site as their base,
# which requires getting persistence into the mix. These objects pickle
# as a name and they look it up in the component registry of their
# __parent__ (first arg)
from zope.component import globalSiteManager as BASE

# This one is a common base for all COPPA sites
BASECOPPA = BaseComponents(BASE, name='genericcoppabase', bases=(BASE,))

# This one serves as a common base for all the other non-COPPA (non-mathcounts) site
# It is not a site of its own
BASEADULT = BaseComponents(BASE, name="genericadultbase", bases=(BASE,))

logger = __import__('logging').getLogger(__name__)


# Things that have moved
import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
    "Import from nti.app.sites.mathcounts",
    "nti.app.sites.mathcounts",
    "MATHCOUNTS",
    "TESTMATHCOUNTS")

zope.deferredimport.deprecatedFrom(
    "Import from nti.app.sites.alpha",
    "nti.app.sites.alpha",
    "ALPHA")

zope.deferredimport.deprecatedFrom(
    "Import from nti.app.sites.columbia",
    "nti.app.sites.columbia",
    "COLUMBIA")

zope.deferredimport.deprecatedFrom(
    "Import from nti.app.sites.demo",
    "nti.app.sites.demo",
    "DEMO")

zope.deferredimport.deprecatedFrom(
    "Import from nti.app.sites.law",
    "nti.app.sites.law",
    "LAW")

zope.deferredimport.deprecatedFrom(
    "Import from nti.app.sites.litworld",
    "nti.app.sites.litworld",
    "LITWORLD")

zope.deferredimport.deprecatedFrom(
    "Import from nti.app.sites.prmia",
    "nti.app.sites.prmia",
    "PRMIA")

zope.deferredimport.deprecatedFrom(
    "Import from nti.app.sites.rwanda",
    "nti.app.sites.rwanda",
    "RWANDA")


def _find_sites():
    """
    By using internal details, find all components
    that are children of the root components declared in this module,
    even if they are not declared in this module.
    The list is returned in roughly top-down order.
    """

    def _collect_subs(components, accum):
        accum.append(components)
        # pylint: disable=protected-access
        for subreg in components.adapters._v_subregistries.keys():
            parent_component = subreg.__parent__
            _collect_subs(parent_component, accum)

    # Find all the extent sub-components of the root
    # components. This is roughly in topological order
    # from the root down
    top_down_components = [BASEADULT, BASECOPPA]
    for top in list(top_down_components):
        _collect_subs(top, top_down_components)

    # Remove dups, preserve order
    result = []
    for x in top_down_components:
        if x not in result:
            result.append(x)
    return result


def _reinit():
    """
    ZCA cleans up the base registry on testing cleanup. It does so by
    leaving the base registry object in place and swizzling out its internals
    by calling ``__init__`` again.

    This means that our site objects no longer have the right resolution order
    (which is cached when bases are set). This in turn means that new
    components derived from them can wind up with the wrong resolution
    order and duplicate registrations (this manifests itself as seeing
    certain event listeners run twice, etc.) The solution is for us to also
    ``__init__`` our site objects. This works because the order of cleanups is maintained
    and so we re-init after ZCA's base registry has re-inited.
    """
    # The order in which we do this matters to some extent. The things that
    # directly have BASE as their __bases__ need to be reset FIRST, followed
    # by things that internally descend from those objects, otherwise we wind up
    # with the wrong resolution order still. Ideally we'd do a topographical
    # sort, but with only two levels that's overkill. The _find_sites
    # does a reasonable approximation.

    for site in _find_sites():
        site.__init__(site.__parent__, name=site.__name__, bases=site.__bases__)


from zope.testing.cleanup import addCleanUp
addCleanUp(_reinit)
