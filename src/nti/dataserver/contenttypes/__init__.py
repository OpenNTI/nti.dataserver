#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This package defines the "generic" objects that implement the IModeledContent interfaces.

Most of the imports in this module itself are backward compatibility re-exports

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# disable unused import warning
# pylint: disable=W0611

# Legacy exports; be careful removing them, some may be in the database...
# ... but not the mixins
# from .threadable import ThreadableMixin
# from .threadable import ThreadableExternalizableMixin
# from .base import UserContentRoot as _UserContentRoot

from nti.dataserver.contenttypes.bookmark import Bookmark

from nti.dataserver.contenttypes.canvas import Canvas
from nti.dataserver.contenttypes.canvas import CanvasShape
from nti.dataserver.contenttypes.canvas import CanvasUrlShape
from nti.dataserver.contenttypes.canvas import CanvasPathShape
from nti.dataserver.contenttypes.canvas import CanvasTextShape
from nti.dataserver.contenttypes.canvas import CanvasCircleShape
from nti.dataserver.contenttypes.canvas import CanvasPolygonShape
from nti.dataserver.contenttypes.canvas import CanvasAffineTransform

from nti.dataserver.contenttypes.canvas import NonpersistentCanvasShape
from nti.dataserver.contenttypes.canvas import NonpersistentCanvasUrlShape
from nti.dataserver.contenttypes.canvas import NonpersistentCanvasPathShape
from nti.dataserver.contenttypes.canvas import NonpersistentCanvasTextShape
from nti.dataserver.contenttypes.canvas import NonpersistentCanvasCircleShape
from nti.dataserver.contenttypes.canvas import NonpersistentCanvasPolygonShape

from nti.dataserver.contenttypes.highlight import Highlight

from nti.dataserver.contenttypes.media import Media
from nti.dataserver.contenttypes.media import EmbeddedMedia
from nti.dataserver.contenttypes.media import EmbeddedVideo
from nti.dataserver.contenttypes.media import EmbeddedAudio

from nti.dataserver.contenttypes.note import Note

from nti.dataserver.contenttypes.redaction import Redaction

# Support for legacy class names in creation
from nti.externalization.internalization import register_legacy_search_module
register_legacy_search_module('nti.dataserver.contenttypes')
register_legacy_search_module('nti.dataserver.contenttypes.note')
register_legacy_search_module('nti.dataserver.contenttypes.canvas')
register_legacy_search_module('nti.dataserver.contenttypes.bookmark')
register_legacy_search_module('nti.dataserver.contenttypes.highlight')
register_legacy_search_module('nti.dataserver.contenttypes.redaction')
