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
# as a name and they look it up in the component registry
from zope.component import globalSiteManager as BASE


MATHCOUNTS = BaseComponents(BASE, name='mathcounts.nextthought.com', bases=(BASE,))
TESTMATHCOUNTS = BaseComponents(BASE, name='testmathcounts.nextthought.com', bases=(MATHCOUNTS,))

ALPHA = BaseComponents(BASE,name='alpha.nextthought.com', bases=(BASE,))
DEMO = BaseComponents(BASE,name='demo.nextthought.com', bases=(BASE,))

RWANDA = BaseComponents(BASE,name='rwanda.nextthought.com', bases=(BASE,))
LAW = BaseComponents(BASE, name='law.nextthought.com', bases=(BASE,))
LITWORLD = BaseComponents(BASE, name='litworld.nextthought.com', bases=(BASE,))
COLLEGIATE = BaseComponents(BASE, name='collegiate.nextthought.com', bases=(BASE,))
GLORIA_MUNDI = BaseComponents(BASE, name='gloria-mundi.nextthought.com', bases=(BASE,))


PRMIA = BaseComponents( BASE, name='prmia.nextthought.com', bases=(BASE,))
FINTECH = BaseComponents( BASE, name='fintech.nextthought.com', bases=(BASE,) )

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
	for v in sys.modules[__name__].__dict__.values():
		if isinstance( v, BaseComponents ):
			v.__init__( BASE, name=v.__name__, bases=v.__bases__ )

from zope.testing.cleanup import addCleanUp
addCleanUp( _reinit )
