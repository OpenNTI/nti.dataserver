#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Component registries and site managers for specific sites.

These use :mod:`z3c.baseregistry` to be configurable using ZCML. Thus,
for each constant declared here, there is a corresponding ZCML file
that registers the constant as a utility with a matching name. Any configuration
for that site belongs in a ``registerIn`` directive within that ZCML file. These
files then have to be referenced from the main configuration file.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
import sys
from z3c.baseregistry.baseregistry import BaseComponents


# TODO: Eventually we want these to use the main Dataserver site as their base,
# which requires getting persistence into the mix. These objects pickle
# as a name and they look it up in the component registry of their __parent__ (first arg)
from zope.component import globalSiteManager as BASE


MATHCOUNTS = BaseComponents(BASE, name='mathcounts.nextthought.com', bases=(BASE,))
TESTMATHCOUNTS = BaseComponents(MATHCOUNTS, name='testmathcounts.nextthought.com', bases=(MATHCOUNTS,))

# This one serves as a common base for all the other non-COPPA (non-mathcounts) site
# It is not a site of its own
BASEADULT = BaseComponents(BASE, name="genericadultbase", bases=(BASE,))

ALPHA = BaseComponents(BASEADULT,name='alpha.nextthought.com', bases=(BASEADULT,))
DEMO = BaseComponents(BASEADULT,name='demo.nextthought.com', bases=(BASEADULT,))

RWANDA = BaseComponents(BASEADULT,name='rwanda.nextthought.com', bases=(BASEADULT,))
LAW = BaseComponents(BASEADULT, name='law.nextthought.com', bases=(BASEADULT,))
LITWORLD = BaseComponents(BASEADULT, name='litworld.nextthought.com', bases=(BASEADULT,))
COLLEGIATE = BaseComponents(BASEADULT, name='collegiate.nextthought.com', bases=(BASEADULT,))
GLORIA_MUNDI = BaseComponents(BASEADULT, name='gloria-mundi.nextthought.com', bases=(BASEADULT,))


PRMIA = BaseComponents(BASEADULT, name='prmia.nextthought.com', bases=(BASEADULT,))
FINTECH = BaseComponents(BASEADULT, name='fintech.nextthought.com', bases=(BASEADULT,))
COLUMBIA = BaseComponents(BASEADULT, name='columbia.nextthought.com', bases=(BASEADULT,))

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
	# sort, but with only two levels that's overkill
	top_level = (BASEADULT, MATHCOUNTS)
	for v in top_level:
		v.__init__( v.__parent__, name=v.__name__, bases=v.__bases__ )

	for v in sys.modules[__name__].__dict__.values():
		if isinstance( v, BaseComponents ):
			if v in top_level:
				continue
			v.__init__( v.__parent__, name=v.__name__, bases=v.__bases__ )

from zope.testing.cleanup import addCleanUp
addCleanUp( _reinit )
