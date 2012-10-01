#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This package defines the "generic" objects that implement the IModeledContent interfaces.

Most of the imports in this module itself are backward compatibility re-exports

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"
# disable unused import warning
#pylint: disable=W0611

from .threadable import ThreadableMixin
from .threadable import ThreadableExternalizableMixin

from .base import UserContentRoot as _UserContentRoot

from .note import Note
from .highlight import Highlight
from .redaction import Redaction

from .canvas import Canvas
from .canvas import CanvasAffineTransform
from .canvas import CanvasCircleShape
from .canvas import CanvasPathShape
from .canvas import CanvasPolygonShape
from .canvas import CanvasShape
from .canvas import CanvasTextShape
from .canvas import CanvasUrlShape

from .canvas import NonpersistentCanvasCircleShape
from .canvas import NonpersistentCanvasPathShape
from .canvas import NonpersistentCanvasPolygonShape
from .canvas import NonpersistentCanvasShape
from .canvas import NonpersistentCanvasTextShape
from .canvas import NonpersistentCanvasUrlShape

# Support for legacy class names in creation
import nti.externalization.internalization
nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.contenttypes' )
nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.contenttypes.note' )
nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.contenttypes.highlight' )
nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.contenttypes.redaction' )
nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.contenttypes.canvas' )
