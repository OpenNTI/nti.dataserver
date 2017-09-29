#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This package defines the "generic" objects that implement the IModeledContent interfaces.

Most of the imports in this module itself are backward compatibility re-exports

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable unused import warning
# pylint: disable=W0611

# Legacy exports; be careful removing them, some may be in the database...
# ... but not the mixins
# from .threadable import ThreadableMixin
# from .threadable import ThreadableExternalizableMixin
# from .base import UserContentRoot as _UserContentRoot

import zope.deferredimport

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

from nti.dataserver.contenttypes.note import Note

from nti.dataserver.contenttypes.redaction import Redaction

zope.deferredimport.initialize()
zope.deferredimport.deprecated(
    "Moved to nti.dataserver.contenttypes.media",
    Media="nti.dataserver.contenttypes.media:Media",
    EmbeddedMedia="nti.dataserver.contenttypes.media:EmbeddedMedia",
    EmbeddedAudio="nti.dataserver.contenttypes.media:EmbeddedAudio",
    EmbeddedVideo="nti.dataserver.contenttypes.media:EmbeddedVideo")
