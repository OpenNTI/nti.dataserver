#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of canvas types.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import numbers
from urllib import quote as urlquote

from zope import component
from zope import interface

from zope.location.interfaces import IContained

from zope.schema.interfaces import WrongType
from zope.schema.interfaces import WrongContainedType

from persistent import Persistent

from persistent.list import PersistentList

from nti.base._compat import text_

from nti.base.interfaces import IFile

from nti.contentfragments.interfaces import IUnicodeContentFragment

from nti.dataserver.contenttypes.base import _make_getitem
from nti.dataserver.contenttypes.base import UserContentRoot

from nti.dataserver.interfaces import ICanvas
from nti.dataserver.interfaces import ICanvasShape
from nti.dataserver.interfaces import ICanvasURLShape
from nti.dataserver.interfaces import ILinkExternalHrefOnly

from nti.externalization.datastructures import InterfaceObjectIO
from nti.externalization.datastructures import ExternalizableInstanceDict

from nti.externalization.externalization import toExternalObject

from nti.externalization.interfaces import IExternalObject
from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IInternalObjectExternalizer

from nti.externalization.oids import to_external_ntiid_oid

from nti.mimetype import mimetype

from nti.mimetype.externalization import decorateMimeType

from nti.threadable.threadable import Threadable as ThreadableMixin

OID = StandardExternalFields.OID
NTIID = StandardExternalFields.NTIID


#####
# Whiteboard shapes
#####


@interface.implementer(ICanvas, IContained)
class Canvas(ThreadableMixin, UserContentRoot):

    # TODO: We're not trying to resolve any incoming external
    # things. Figure out how we want to do incremental changes
    # (pushing new shapes while drawing). Should we take the whole thing every
    # time (and then look for equal object that we already have)? Accept POSTS
    # of shapes into this object as a "container"? Right now, we have disabled
    # persistence of individual shapes so it doesn't do us much good. We do at least
    # preserve the PersistentList, when possible.
    __name__ = None
    __parent__ = None

    viewportRatio = 1.0

    def __init__(self):
        super(Canvas, self).__init__()
        self.shapeList = PersistentList()

    def append(self, shape):
        if not isinstance(shape, _CanvasShape):
            __traceback_info__ = shape
            raise WrongContainedType()
        self.shapeList.append(shape)
        shape.__parent__ = self
        shape.__name__ = text_(len(self.shapeList) - 1)

    __getitem__ = _make_getitem('shapeList')

    def __eq__(self, other):
        # TODO: Super properties?
        try:
            return self.shapeList == other.shapeList
        except AttributeError:  # pragma: no cover
            return NotImplemented

    def __hash__(self):
        return hash(tuple(self.shapeList))

    def __len__(self):
        """
        The size of a canvas is how many shapes it contains.
        """
        return len(self.shapeList)

    def __nonzero__(self):
        """
        Canvas objects are always true, even when containing no shapes.
        """
        return True


from nti.dataserver.contenttypes.base import UserContentRootInternalObjectIO

from nti.threadable.externalization import ThreadableExternalizableMixin


@component.adapter(ICanvas)
class CanvasInternalObjectIO(ThreadableExternalizableMixin,
                             UserContentRootInternalObjectIO):

    # TODO: We're not trying to resolve any incoming external
    # things. Figure out how we want to do incremental changes
    # (pushing new shapes while drawing). Should we take the whole thing every
    # time (and then look for equal object that we already have)? Accept POSTS
    # of shapes into this object as a "container"? Right now, we have disabled
    # persistence of individual shapes so it doesn't do us much good. We do at least
    # preserve the PersistentList, when possible.

    # We write shapes ourself for speed. The list is often long and only
    # contains _CanvasShape "objects". Note that this means they cannot be
    # decorated

    _user_root_excluded_out_ivars_ = getattr(UserContentRootInternalObjectIO, '_excluded_out_ivars_')
    _excluded_out_ivars_ = _user_root_excluded_out_ivars_.union(('shapeList', 'viewportRatio'))

    def updateFromExternalObject(self, ext_parsed, **kwargs):
        canvas = self.context
        # Special handling of shapeList to preserve the PersistentList.
        # (Though this may or may not matter. See the note at the top of the class)
        shapeList = ext_parsed.pop('shapeList', self)
        viewportRatio = ext_parsed.pop('viewportRatio', self)
        super(CanvasInternalObjectIO, self).updateFromExternalObject(ext_parsed, **kwargs)
        # check viewportRatio
        if 		isinstance(viewportRatio, numbers.Real) \
            and viewportRatio > 0 \
            and viewportRatio != canvas.viewportRatio:
            canvas.viewportRatio = viewportRatio
        # check files
        if shapeList is not self:
            # Save existing files, if we can detect for sure that
            # it's the same image
            for shape in shapeList:
                try:
                    adopt = shape._adopt_file_if_same
                    # We must have the correct parent already set or it
                    # gets a reference to the wrong one
                    shape.__parent__ = canvas
                except AttributeError:
                    continue
                else:
                    for existing_shape in canvas.shapeList:
                        if adopt(existing_shape):
                            break
            del canvas.shapeList[:]
            if shapeList:
                for shape in shapeList:
                    canvas.append(shape)
            # be polite and put it back
            ext_parsed['shapeList'] = list(self.context.shapeList)

    def toExternalObject(self, mergeFrom=None, **kwargs):
        result = super(CanvasInternalObjectIO, self).toExternalObject(mergeFrom=mergeFrom, **kwargs)
        result['shapeList'] = [x.toExternalObject(**kwargs) for x in self.context.shapeList]
        result['viewportRatio'] = self.context.viewportRatio
        return result


@component.adapter(ICanvas)
@interface.implementer(IInternalObjectExternalizer)
class _CanvasExporter(InterfaceObjectIO):

    _ext_iface_upper_bound = ICanvas

    def toExternalObject(self, **kwargs):
        context = self._ext_replacement()
        [kwargs.pop(x, None) for x in ('name', 'decorate')]
        adapter = IInternalObjectExternalizer(context, None)
        if adapter is not None:
            result = adapter.toExternalObject(decorate=False, name='exporter',
                                               **kwargs)
        else:
            result = super(_CanvasExporter, self).toExternalObject(decorate=False, 
                                                                   name='exporter',
                                                                   **kwargs)
            decorateMimeType(context, result)
        [result.pop(x, None) for x in (OID, NTIID)]
        return result


@interface.implementer(IExternalObject)
class CanvasAffineTransform(object):
    """
    Represents the 6 values required in an 2-D affine transform:
    \|a  b  0|
    \|c  d  0|
    \|tx ty 1|

    Treated are like structs, compared by value, not identity. They are
    never standalone, so many of their external fields are lacking. They handle
    all their own externalization and are not meant to be subclassed.
    """
    __metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

    __external_can_create__ = True

    __slots__ = ('a', 'b', 'c', 'd', 'tx', 'ty')

    A = D = 1
    B = C = TX = TY = 0

    def __init__(self, a=1, b=0, c=0, d=1, tx=0, ty=0):
        """
        Initializes to the identity transform.
        """
        # cannot mix __slots__ with class attributes
        self.a = a
        self.d = d
        self.b = b
        self.c = c
        self.tx = tx
        self.ty = ty

    def updateFromExternalObject(self, parsed, **unused_kwargs):
        for k in self.__slots__:
            if k in parsed:
                val = parsed[k]
                __traceback_info__ = k, val
                if not isinstance(val, numbers.Number):
                    # match the schema-driven updates
                    raise WrongType(val, numbers.Number, k)
                setattr(self, k, val)

    def toExternalDictionary(self, *unused_args, **unused_kwargs):
        """
        Note that we externalize ourself directly, without going through the superclass
        at all, for speed. We would only delete most of the stuff it added anyway.
        """
        result = LocatedExternalDict(a=self.a,
                                     b=self.b,
                                     c=self.c,
                                     d=self.d,
                                     tx=self.tx,
                                     ty=self.ty,
                                     Class=self.__class__.__name__,
                                     MimeType=self.mime_type)
        return result

    def toArray(self):
        return [self.a, self.b, self.c, self.d, self.tx, self.ty]

    def toExternalObject(self, *args, **kwargs):
        return self.toExternalDictionary(*args, **kwargs)

    def __eq__(self, other):
        try:
            return all([getattr(self, x) == getattr(other, x) for x in self.__slots__])
        except AttributeError:  # pragma: no cover
            return NotImplemented

    def __hash__(self):
        return hash(tuple([getattr(self, x) for x in self.__slots__]))


from nti.dataserver.contenttypes.color import createColorProperty
from nti.dataserver.contenttypes.color import updateColorFromExternalValue


@interface.implementer(ICanvasShape, IExternalObject)
class _CanvasShape(ExternalizableInstanceDict):

    __name__ = None
    __parent__ = None
    __metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

    # We generate the affine transform on demand; we don't store it
    # to avoid object overhead.

    _a = _d = CanvasAffineTransform.A
    _b = _c = _tx = _ty = CanvasAffineTransform.TY

    createColorProperty('fill', opacity=0.0)
    createColorProperty('stroke')

    def __init__(self):
        super(_CanvasShape, self).__init__()

        # stroke width is the same both platforms, and stored in pts.
        self._stroke_width = 1.0

    def get_transform(self):
        result = CanvasAffineTransform()
        for x in result.__slots__:
            val = getattr(self, '_' + x)
            if val != getattr(result, x):
                setattr(result, x, val)
        return result

    def set_transform(self, matrix):
        __traceback_info__ = matrix
        assert isinstance(matrix, CanvasAffineTransform)
        for x in matrix.__slots__:
            val = getattr(matrix, x)
            if val != getattr(self, '_' + x):
                setattr(self, '_' + x, val)

    transform = property(get_transform, set_transform)

    @property
    def strokeWidth(self):
        return "{:.3%}".format(self._stroke_width / 100)

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        super(_CanvasShape, self).updateFromExternalObject(parsed, *args, **kwargs)
        # The matrix, if given, convert to our points
        matrix = parsed.pop('transform', None)
        if matrix:
            self.transform = matrix

        # If stroke/fill rgba are given, they take precedence.
        updateColorFromExternalValue(self, 'fill', parsed)
        updateColorFromExternalValue(self, 'stroke', parsed)

        stroke_width = parsed.pop('strokeWidth', None)
        if stroke_width is not None:  # maybe string or float
            if isinstance(stroke_width, six.string_types):
                if stroke_width.endswith('%'):
                    stroke_width = stroke_width[0:-1]
                # Basic b/w compat
                elif stroke_width.endswith('pt'):
                    stroke_width = stroke_width[0:-2]
            stroke_width = float(stroke_width)
            assert stroke_width >= 0.0
            assert stroke_width <= 100.0
            self._stroke_width = stroke_width

    def toExternalDictionary(self, mergeFrom=None, *args, **kwargs):
        # Implementation note: For now, because we are not
        # doing anything fancy with keeping track of identical objects
        # when we update a canvas, we are also eliding these same fields like
        # Point.
        mergeFrom = mergeFrom or {}
        # Avoid the creation of a temporary object and externalize directly
        mergeFrom['transform'] = LocatedExternalDict(a=self._a, b=self._b, c=self._c, d=self._d,
                                                     tx=self._tx, ty=self._ty,
                                                     Class=CanvasAffineTransform.__name__,
                                                     MimeType=CanvasAffineTransform.mime_type)
        # self.transform.toExternalDictionary()

        mergeFrom['strokeRGBAColor'] = self.strokeRGBAColor
        mergeFrom['fillRGBAColor'] = self.fillRGBAColor

        mergeFrom['strokeColor'] = self.strokeColor
        mergeFrom['strokeOpacity'] = self.strokeOpacity
        mergeFrom['strokeWidth'] = self.strokeWidth

        mergeFrom['fillColor'] = self.fillColor
        mergeFrom['fillOpacity'] = self.fillOpacity

        return super(_CanvasShape, self).toExternalDictionary(mergeFrom=mergeFrom, *args, **kwargs)
    # Avoid the call to standard_dictionary, and just use the minimal fields
    __external_use_minimal_base__ = True

    def toExternalObject(self, *args, **kwargs):
        return self.toExternalDictionary(*args, **kwargs)

    def __eq__(self, other):
        # Implementation note: when toExternalDictionary changes,
        # this method should change too
        # TODO: This is a lousy comparison
        try:
            return self.transform == other.transform
        except AttributeError:
            return NotImplemented

    def __hash__(self):
        return hash(self.transform)


class _CanvasCircleShape(_CanvasShape):
    pass


class _CanvasPolygonShape(_CanvasShape):

    _ext_primitive_out_ivars_ = _CanvasShape._ext_primitive_out_ivars_.union({'sides'})

    def __init__(self, sides=4):
        super(_CanvasPolygonShape, self).__init__()
        self.sides = sides

    def updateFromExternalObject(self, *args, **kwargs):
        super(_CanvasPolygonShape, self).updateFromExternalObject(*args, **kwargs)
        assert isinstance(self.sides, numbers.Integral)

    def __eq__(self, other):
        try:
            return super(_CanvasPolygonShape, self).__eq__(other) and self.sides == other.sides
        except AttributeError:
            return NotImplemented

    def __hash__(self):
        return super(_CanvasPolygonShape, self).__hash__() + self.sides


class _CanvasTextShape(_CanvasShape):

    _ext_primitive_out_ivars_ = _CanvasShape._ext_primitive_out_ivars_.union({'text'})

    def __init__(self, text=''):
        super(_CanvasTextShape, self).__init__()
        self.text = text

    def updateFromExternalObject(self, *args, **kwargs):
        tbf = self.text
        super(_CanvasTextShape, self).updateFromExternalObject(*args, **kwargs)
        assert isinstance(self.text, six.string_types)
        if self.text != tbf:
            self.text = component.getAdapter(self.text, IUnicodeContentFragment,
											 name='text')


from nti.links.links import Link

from nti.property.property import alias

from nti.property.urlproperty import UrlProperty


@interface.implementer(ICanvasURLShape)
class _CanvasUrlShape(_CanvasShape):

    # We take responsibility for writing the URL ourself
    _excluded_out_ivars_ = _CanvasShape._excluded_out_ivars_.union({'url'})
    _ext_primitive_out_ivars_ = _CanvasShape._ext_primitive_out_ivars_.union({'url'})

    _file = None
    file = alias('_file')

    _DATA_NAME = 'data'

    def __init__(self, url=''):
        super(_CanvasUrlShape, self).__init__()
        self.url = url

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        url = parsed.pop('url', None)
        super(_CanvasUrlShape, self).updateFromExternalObject(parsed, *args, **kwargs)
        if IFile.providedBy(url):
            self._file = url
            self._file.__parent__ = self.__parent__
        else:
            self.url = url

    url = UrlProperty(data_name=_DATA_NAME,
                      url_attr_name='url',
                      file_attr_name='_file',
                      use_dict=True)

    __getitem__ = url.make_getitem()

    def toExternalDictionary(self, mergeFrom=None, *args, **kwargs):
        result = super(_CanvasUrlShape, self).toExternalDictionary(mergeFrom=mergeFrom, *args, **kwargs)
        if self._file is not None:
            # See __getitem__
            # TODO: This is pretty tightly coupled to the app layer
            # TODO: If we wanted to be clever, we would have a cutoff point based on the size
            # to determine when to return a link vs the data URL.
            # We do not want to rely on traversal to this object, so we give the exact
            # NTIID path to the file. (Traversal works for pure canvas, and canvas-in-note, but breaks
            # for canvas-in-chat-message)
            if kwargs.get('name', None) == 'exporter':
                result['url'] = toExternalObject(self._file, name='exporter',
                                                 decorate=False)
            else:
                target = to_external_ntiid_oid(self._file, add_to_connection=True)
                if target:
                    link = Link(target=target,
                                target_mime_type=self._file.mimeType,
                                elements=('@@view',), rel="data")
                    interface.alsoProvides(link, ILinkExternalHrefOnly)
                    result['url'] = link
                else:
                    logger.warn("Unable to produce URL for file data in %s", self)
                    result['url'] = self.url
        else:
            result['url'] = self.url
        return result

    def _adopt_file_if_same(self, existing_shape):
        """
        Is this object, which should not already be persistent, meant to
        be pointing to the same data as an existing shape? If so, make
        this object share the same data. Note that we assume parentage
        of the file object.
        """
        if not isinstance(existing_shape, _CanvasUrlShape):
            return
        if (   self is existing_shape  # same object
            or self._file is not None  # we already have a file
            or not self.url):  # We don't have a URL to compare to
            return

        existing_file = existing_shape._file
        if existing_file is None:  # Not a file
            return

        existing_link = to_external_ntiid_oid(existing_file)
        if existing_link and urlquote(existing_link) in self.url:
            # Yes, we have a match
            self._file = existing_file
            self._file.__parent__ = self.__parent__
            self.__dict__['url'] = None
            return True

    def __repr__(self):
        return '<%s>' % self.__class__.__name__


class _CanvasPathShape(_CanvasShape):

    # We write points ourself for speed. The list is often long and only
    # contains primitives.
    _excluded_out_ivars_ = _CanvasShape._excluded_out_ivars_.union({'points'})

    _ext_primitive_out_ivars_ = _CanvasShape._ext_primitive_out_ivars_.union({'closed'})

    def __init__(self, closed=True, points=()):
        super(_CanvasPathShape, self).__init__()
        self.closed = closed
        self.points = points

    def updateFromExternalObject(self, *args, **kwargs):
        super(_CanvasPathShape, self).updateFromExternalObject(*args, **kwargs)
        assert (   isinstance(self.closed, bool)
                or self.closed == 0 or self.closed == 1)
        if self.closed == 0 or self.closed == 1:
            self.closed = bool(self.closed)
        for i in self.points:
            assert isinstance(i, numbers.Real)
        assert (len(self.points) % 2) == 0  # Must be even number of pairs

    def toExternalDictionary(self, mergeFrom=None, *args, **kwargs):
        result = super(_CanvasPathShape, self).toExternalDictionary(mergeFrom=mergeFrom, *args, **kwargs)
        result['points'] = self.points
        return result

    def __eq__(self, other):
        try:
            return  super(_CanvasPathShape, self).__eq__(other) \
                and self.closed == other.closed \
                and self.points == other.points
        except AttributeError:
            return NotImplemented

    def __hash__(self):
        return super(_CanvasPathShape, self).__hash__()

# ## Ok, so earlier we screwed up. We had CanvasShape by default
# be persistent. We need the class with that name to continue to be persistent,
# otherwise we cannot load them out of the database. But we want new objects
# to not be persistent, hence the class layout that has non-externally-creatable
# objects at the root, then a persistent subclass that's also not creatable,
# and then a non-persistent subclass that is creatable, but registered
# under all the old names and indistinguishable from outside.
# A migration has moved all old objects to the new version;
# now we need to deprecate the old version and be sure that they don't
# get loaded anymore, then we can delete the class


class CanvasShape(_CanvasShape, Persistent):
    pass


class CanvasUrlShape(_CanvasUrlShape, Persistent):
    pass


class CanvasPathShape(_CanvasPathShape, Persistent):
    pass


class CanvasTextShape(_CanvasTextShape, Persistent):
    pass


class CanvasCircleShape(_CanvasCircleShape, Persistent):
    pass


class CanvasPolygonShape(_CanvasPolygonShape, Persistent):
    pass


class NonpersistentCanvasShape(_CanvasShape):
    __external_can_create__ = True
    mime_type = CanvasShape.mime_type
    __external_class_name__ = 'CanvasShape'


class NonpersistentCanvasCircleShape(_CanvasCircleShape):
    __external_can_create__ = True
    mime_type = CanvasCircleShape.mime_type
    __external_class_name__ = 'CanvasCircleShape'


class NonpersistentCanvasPolygonShape(_CanvasPolygonShape):
    __external_can_create__ = True
    mime_type = CanvasPolygonShape.mime_type
    __external_class_name__ = 'CanvasPolygonShape'


class NonpersistentCanvasTextShape(_CanvasTextShape):
    __external_can_create__ = True
    mime_type = CanvasTextShape.mime_type
    __external_class_name__ = 'CanvasTextShape'


class NonpersistentCanvasUrlShape(_CanvasUrlShape):
    __external_can_create__ = True
    mime_type = CanvasUrlShape.mime_type
    __external_class_name__ = 'CanvasUrlShape'


class NonpersistentCanvasPathShape(_CanvasPathShape):
    __external_can_create__ = True
    mime_type = CanvasPathShape.mime_type
    __external_class_name__ = 'CanvasPathShape'
