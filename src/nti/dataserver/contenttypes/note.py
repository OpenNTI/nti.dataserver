#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definition of the Note object.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six

from zope import component
from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.schema.fieldproperty import FieldProperty

from nti.base.interfaces import IFile

from nti.coremetadata.schema import BodyFieldProperty

from nti.dataserver.contenttypes.base import _make_getitem

from nti.dataserver.contenttypes.highlight import Highlight
from nti.dataserver.contenttypes.highlight import HighlightInternalObjectIO

from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IMedia
from nti.dataserver.interfaces import ICanvas
from nti.dataserver.interfaces import IRatable
from nti.dataserver.interfaces import ILikeable
from nti.dataserver.interfaces import IFlaggable
from nti.dataserver.interfaces import IFavoritable

from nti.externalization.interfaces import IClassObjectFactory 

from nti.externalization.internalization import update_from_external_object

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.threadable.externalization import ThreadableExternalizableMixin

from nti.threadable.threadable import Threadable as ThreadableMixin

# Ownership (containment) and censoring are already taken care of by the
# event listeners on IBeforeSequenceAssignedEvent
BodyFieldProperty = BodyFieldProperty  # BWC alias

_style_field = INote['style'].bind(None)
_style_field.default = 'suppressed'

logger = __import__('logging').getLogger(__name__)


@interface.implementer(INote,
                       # requires annotations
                       ILikeable,
                       IFavoritable,
                       IFlaggable,
                       IRatable,
                       # provides annotations
                       IAttributeAnnotatable)
class Note(ThreadableMixin, Highlight):
    """
    Implementation of a note.
    """

    #: A sequence of properties we would like to copy from the parent
    #: when a child reply is created. If the child already has them, they
    #: are left alone.
    #: This consists of the anchoring properties, and for some reason the title
    _inheritable_properties_ = ('applicableRange', 'title')

    #: We override the default highlight style to suppress it.
    style = FieldProperty(_style_field)

    # uses the 'body' in the dict, which is compatible with persistent objects
    body = BodyFieldProperty(INote['body'])

    title = FieldProperty(INote['title'])

    def __init__(self):
        super(Note, self).__init__()

    __getitem__ = _make_getitem('body')



@component.adapter(INote)
class NoteInternalObjectIO(ThreadableExternalizableMixin, HighlightInternalObjectIO):

    def _resolve_external_body(self, context, unused_parsed, body):
        """
        Attempt to resolve elements in the body to existing canvas objects
        that are my children. If we find them, then update them in place
        to the best of our ability.
        """
        note = self.context
        if not note or not note.body or note.body == ("",):
            # Our initial state. Empty body, nothing to resolve against.
            return body

        # Support raw body, not wrapped
        if isinstance(body, six.string_types):
            body = [body]

        for i, item in enumerate(body):
            if not (	ICanvas.providedBy(item)
                     or IMedia.providedBy(item)
                     or IFile.providedBy(item)):
                continue

            ext_val = getattr(item, '_v_updated_from_external_source', {})
            if 'NTIID' not in ext_val:
                continue

            existing_object = find_object_with_ntiid(ext_val['NTIID'])
            if getattr(existing_object, '__parent__', None) is not note:
                continue

            # Ok, so we found one of my children. Update it in place. Don't notify for it,
            # so that it doesn't falsely get in a stream or whatever
            __traceback_info__ = i, item, ext_val, existing_object, note
            update_from_external_object(existing_object,
                                        ext_val,
                                        context=context,
                                        notify=False)
            try:
                existing_object.updateLastMod()
            except AttributeError:
                pass
            body[i] = existing_object
            assert body[i].__parent__ is note
            self._x = existing_object
        return body

    __external_resolvers__ = {'body': _resolve_external_body}

    def toExternalObject(self, mergeFrom=None, **kwargs):
        ext = super(NoteInternalObjectIO, self).toExternalObject(mergeFrom=mergeFrom, **kwargs)
        # don't write out the base state, it confuses updating and isn't valid
        if ext['body'] in (Note.body, [''], None):
            del ext['body']
        return ext

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        # Only updates to the body are accepted
        parsed.pop('text', None)
        super(NoteInternalObjectIO, self).updateFromExternalObject(parsed, *args, **kwargs)

        note = self.context

        # If we are newly created, and a reply, then
        # we want to use our policy settings to determine the sharing
        # of the new note. This is because our policy settings
        # may be user/community/context specific.
        if not note._p_mtime and note.inReplyTo:
            # Current policy is to copy the sharing settings
            # of the parent, and share back to the parent's creator,
            # only making sure not to share with ourself since that's weird
            # (Be a bit defensive about bad inReplyTo)
            if not hasattr(note.inReplyTo, 'sharingTargets'):  # pragma: no cover
                raise AttributeError('Illegal value for inReplyTo: %s' % note.inReplyTo)
            sharingTargets = set(note.inReplyTo.sharingTargets)
            sharingTargets.add(note.inReplyTo.creator)
            sharingTargets.discard(note.creator)
            sharingTargets.discard(None)

            note.updateSharingTargets(sharingTargets)

            # Now some other things we want to inherit if possible
            for copy in note._inheritable_properties_:
                val = getattr(note.inReplyTo, copy, getattr(note, copy, None))
                if val is not None:
                    setattr(note, copy, val)


@interface.implementer(IClassObjectFactory)
class NoteFactory(object):
    
    description = title = "Note factory"

    def __init__(self, *args):
        pass

    def __call__(self, *unused_args, **unused_kw):
        return Note()

    def getInterfaces(self):
        return (INote,)
