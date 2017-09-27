#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.async.utils.processor import Processor

from nti.dataserver import SESSION_CLEANUP_QUEUE

from nti.dataserver.utils.base_script import create_context


class SessionProcessor(Processor):

    def create_context(self, env_dir, args=None):
        context = create_context(env_dir, with_library=False)
        return context

    def process_args(self, args):
        setattr(args, 'redis', True)
        setattr(args, 'library', False)
        setattr(args, 'queue_names', SESSION_CLEANUP_QUEUE)
        super(SessionProcessor, self).process_args(args)


def main():
    return SessionProcessor()()


if __name__ == '__main__':
    main()
