#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

--------
Versions
--------

Nothing seems to actually be supporting the same
WebSocket protocol versions.

Firefox
-------
Firefox 5 and 6 have nothing. Socket.io uses
long-connections with xhr-multipart for it.

Safari
------
All tested versions of Safari (5.1 lion, 5.0 on lion,
nightly) seems to run version 76 of the protocol (KEY1
and KEY2), and so it connects just fine over websockets.
NOTE: the source document must be served over HTTP.
Local files don't work without a hack to avoid checking HTTP_ORIGIN

Safari on iOS 5 is the same as desktop.

Chrome
------
Chrome 14.0.835.122 beta is the new version 7 or 8.
Chrome 15.0.865.0 dev is the same as Chrome 14.
Chrome 16 is version 13 (which seems to be compatible with 7/8)


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"
