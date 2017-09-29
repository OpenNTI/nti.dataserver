#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import greater_than
from hamcrest import has_property
from hamcrest import only_contains

from zope.schema.interfaces import WrongType

from nti.contentrange.contentrange import ContentRangeDescription

from nti.dataserver.contenttypes.bookmark import Bookmark as _Bookmark

from nti.dataserver.contenttypes.highlight import Highlight as _Highlight

from nti.dataserver.contenttypes.note import Note as _Note

from nti.dataserver.contenttypes.redaction import Redaction as _Redaction

from nti.dataserver.contenttypes.canvas import Canvas
from nti.dataserver.contenttypes.canvas import CanvasShape
from nti.dataserver.contenttypes.canvas import CanvasUrlShape
from nti.dataserver.contenttypes.canvas import CanvasPathShape
from nti.dataserver.contenttypes.canvas import CanvasCircleShape
from nti.dataserver.contenttypes.canvas import CanvasPolygonShape
from nti.dataserver.contenttypes.canvas import CanvasAffineTransform

from nti.externalization.externalization import to_external_object

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.links.links import Link

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest


def Note():
    n = _Note()
    n.applicableRange = ContentRangeDescription()
    return n


def Bookmark():
    h = _Bookmark()
    h.applicableRange = ContentRangeDescription()
    return h


def Highlight():
    h = _Highlight()
    h.applicableRange = ContentRangeDescription()
    return h


def Redaction():
    h = _Redaction()
    h.applicableRange = ContentRangeDescription()
    return h


GIF_DATAURL = 'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='


class TestCanvas(DataserverLayerTest):

    def test_canvas_affine_transform_external(self):

        with self.assertRaises(WrongType):
            CanvasAffineTransform().updateFromExternalObject({'a': None})

    @WithMockDS
    def test_external(self):
        canvas = Canvas()
        shape1 = CanvasPolygonShape(sides=3)
        shape2 = CanvasCircleShape()
        tx = CanvasAffineTransform()
        tx.a = 5
        tx.ty = 42
        shape2.transform = tx
        canvas.append(shape1)
        canvas.append(shape2)

        ext = to_external_object(canvas)
        tx_ext_list = ('Class', 'CanvasAffineTransform', 'a', 1,
                       'b', 0, 'c', 0, 'd', 1, 'tx', 0, 'ty', 0)
        tx_ext = has_entries(*tx_ext_list)

        def_fill_stroke = {
            'strokeRGBAColor': u'1.000 1.000 1.000',
            'fillRGBAColor': u'1.000 1.000 1.000 0.00',
            'strokeOpacity': 1.0,
            'strokeWidth': u'1.000%',
            'fillColor': u'rgb(255.0,255.0,255.0)',
            'fillOpacity': 0.0,
            'strokeColor': u'rgb(255.0,255.0,255.0)'
        }
        shape1_ext = {
            'Class': 'CanvasPolygonShape',
            'sides': 3, 
            'transform': tx_ext
        }
        tx_ext = list(tx_ext_list)
        tx_ext[tx_ext.index('a') + 1] = 5
        tx_ext[tx_ext.index('ty') + 1] = 42
        tx_ext = has_entries(*tx_ext)
        shape2_ext = {'Class': 'CanvasCircleShape', 'transform': tx_ext}
        shape1_ext.update(def_fill_stroke)
        shape2_ext.update(def_fill_stroke)

        shape1_has_items = []
        map(shape1_has_items.extend, shape1_ext.iteritems())

        shape2_has_items = []
        map(shape2_has_items.extend, shape2_ext.iteritems())

        assert_that(ext, has_entries('Class', 'Canvas',
                                     'shapeList', only_contains(has_entries(*shape1_has_items), 
                                                                has_entries(*shape2_has_items)),
                                     'viewportRatio', 1.0,
                                     'CreatedTime', canvas.createdTime))

        ext['ContainerId'] = u'CID'
        ext['viewportRatio'] = 2.0
        canvas2 = Canvas()
        ds = self.ds
        with mock_dataserver.mock_db_trans(ds):
            update_from_external_object(canvas2, ext, context=ds)

        assert_that(canvas2, is_(canvas))
        assert_that(canvas2.containerId, is_('CID'))
        assert_that(canvas2.viewportRatio, is_(2.0))
        shape3 = CanvasPathShape(closed=False, points=[1, 2.5])
        shape = CanvasPathShape()
        with mock_dataserver.mock_db_trans(ds):
            update_from_external_object(shape, shape3.toExternalObject(), 
                                        context=ds)
        assert_that(shape, is_(shape3))

    @WithMockDS
    def test_canvas_url_shape_external(self):
        ds = self.ds
        shape3 = CanvasUrlShape(url=GIF_DATAURL)
        with mock_dataserver.mock_db_trans(ds):
            shape3.__parent__ = self.ds.root
            ext_shape = shape3.toExternalObject()
            
            assert_that(ext_shape, has_entry('url', is_(Link)))
            ext_shape['url'] = shape3.url  # as string

            shape = CanvasUrlShape()
            shape.__parent__ = self.ds.root

            update_from_external_object(shape, ext_shape, context=ds)

            assert_that(shape, is_(shape3))
            assert_that(shape, has_property('url', GIF_DATAURL))

            assert_that(to_external_object(shape), has_entry('url', is_(Link)))
            assert_that(shape3.__dict__, 
                        has_entry('_file', has_property('mimeType', b'image/gif')))

        shape4 = CanvasUrlShape(url='/path/to/relative/image.png')
        shape = CanvasUrlShape()
        with mock_dataserver.mock_db_trans(ds):
            update_from_external_object(shape, shape4.toExternalObject(), 
                                        context=ds)
        assert_that(shape, is_(shape4))

        assert_that(to_external_object(shape), 
                    has_entry('url', '/path/to/relative/image.png'))

        # Null values for the URL are currently allowed
        with mock_dataserver.mock_db_trans(ds):
            update_from_external_object(shape, {'url': None}, context=ds)

        assert_that(to_external_object(shape), has_entry('url', None))

    @WithMockDS
    def test_external_legacy_factory(self):
        for name in ('Canvas', 'CanvasShape', 'CanvasUrlShape', 'CanvasCircle',
                     'CanvasPathShape', 'CanvasTextShape', 'CanvasPolygonShape',
                     'CanvasCircleShape'):
            ext_obj = {"Class": name}
            factory = find_factory_for(ext_obj)
            assert_that(factory, is_not(none()))
            if name != 'CanvasCircle':
                value = factory()
                assert_that(value, 
                            has_property('__external_class_name__', is_(name)))
        
    @WithMockDS
    def test_canvas_with_urls_updated_keeps_same_objects(self):
        ds = self.ds

        data_url_shape = CanvasUrlShape(url=GIF_DATAURL)
        old_canvas = Canvas()
        old_canvas.append(data_url_shape)
        ext_data_url_shape = to_external_object(data_url_shape)
        ext_canvas = to_external_object(old_canvas)
        with mock_dataserver.mock_db_trans(ds):
            canvas = Canvas()
            ds.root['canvas'] = canvas
            update_from_external_object(canvas, ext_canvas, context=ds)

        # Check values in a new transaction
        with mock_dataserver.mock_db_trans(ds):
            canvas = ds.root['canvas']
            assert_that(canvas, has_property('_p_mtime', greater_than(0)))
            canvas_oid = canvas._p_oid

            assert_that(canvas.shapeList, 
                        has_property('_p_mtime', greater_than(0)))
            shape_list_oid = canvas.shapeList._p_oid

            # The url shape
            assert_that(canvas.shapeList[0], 
                        has_property('_file', has_property('_p_mtime', greater_than(0))))
            file_oid = canvas.shapeList[0]._file._p_oid

        # If we update from the exact same values, nothing changes
        with mock_dataserver.mock_db_trans(ds):
            canvas = ds.root['canvas']
            update_from_external_object(canvas, ext_canvas, context=ds)

            assert_that(canvas, has_property('_p_oid', canvas_oid))
            assert_that(canvas.shapeList, 
                        has_property('_p_oid', shape_list_oid))
            assert_that(canvas.shapeList[0]._file,
                        has_property('_p_oid', file_oid))

        # We can add an additional shape to the list using data, and it gets its own file, but nothing
        # else changes
        with mock_dataserver.mock_db_trans(ds):
            ext_canvas['shapeList'].append(ext_data_url_shape)
            canvas = ds.root['canvas']
            update_from_external_object(canvas, ext_canvas, context=ds)

        with mock_dataserver.mock_db_trans(ds):
            canvas = ds.root['canvas']
            assert_that(canvas, has_property('_p_oid', canvas_oid))
            assert_that(canvas.shapeList, 
                        has_property('_p_oid', shape_list_oid))
            assert_that(canvas.shapeList[0]._file,
                        has_property('_p_oid', file_oid))
            assert_that(canvas.shapeList[1]._file,
                        has_property('_p_oid', is_not(file_oid)))

    def test_update_stroke_width(self):
        c = CanvasShape()
        update_from_external_object(c, {"strokeWidth": u"3.2pt"})
        assert_that(c.strokeWidth, is_("3.200%"))

        update_from_external_object(c, {"strokeWidth": u"3.2"})
        assert_that(c.strokeWidth, is_("3.200%"))

        update_from_external_object(c, {"strokeWidth": u"2.4%"})
        assert_that(c.strokeWidth, is_("2.400%"))

        update_from_external_object(c, {"strokeWidth": u"99.93%"})
        assert_that(c.strokeWidth, is_("99.930%"))

        update_from_external_object(c, {"strokeWidth": 0.743521})
        assert_that(c._stroke_width, is_(0.743521))
        assert_that(c.strokeWidth, is_("0.744%"))

        update_from_external_object(c, {"strokeWidth": 0.3704})
        assert_that(c._stroke_width, is_(0.3704))
        assert_that(c.strokeWidth, is_("0.370%"))

        with self.assertRaises(AssertionError):
            update_from_external_object(c, {"strokeWidth": -1.2})

        with self.assertRaises(AssertionError):
            update_from_external_object(c, {"strokeWidth": 100.1})

    def test_update_shape_rgba(self):
        check_update_props('strokeRGBAColor')
        check_update_props('fillRGBAColor', 'fillColor', 'fillOpacity', 1.0)


def check_update_props(ext_name='strokeRGBAColor',
                       col_name='strokeColor',
                       opac_name='strokeOpacity',
                       def_opac=1.0):

    c = CanvasShape()

    def get_col():
        return getattr(c, col_name)

    def get_opac():
        return getattr(c, opac_name)

    def get_ext(): 
        return getattr(c, ext_name)

    update_from_external_object(c, {ext_name: u"1.0 0.5 0.5"})
    assert_that(get_col(), is_("rgb(255.0,127.5,127.5)"))
    assert_that(get_opac(), is_(def_opac))

    update_from_external_object(c, {ext_name: u"1.0 0.5 0.3 0.5"})
    assert_that(get_opac(), is_(0.5))
    assert_that(get_col(), is_("rgb(255.0,127.5,76.5)"))

    # Updating again without opacity cause opacity to go back to default
    update_from_external_object(c, {ext_name: u"1.0 0.5 0.5"})
    assert_that(get_col(), is_("rgb(255.0,127.5,127.5)"))
    assert_that(get_opac(), is_(1.0))

    update_from_external_object(c, {opac_name: 0.75})
    assert_that(get_col(), is_("rgb(255.0,127.5,127.5)"))
    assert_that(get_opac(), is_(0.75))
    assert_that(get_ext(), is_("1.000 0.500 0.500 0.75"))

    update_from_external_object(c, {col_name: u"rgb( 221.0, 128.1,21.0   )"})
    assert_that(get_opac(), is_(0.75))
    assert_that(get_col(), is_("rgb(221.0,128.1,21.0)"))
    assert_that(get_ext(), is_("0.867 0.502 0.082 0.75"))

    update_from_external_object(c, 
                                {col_name: u"rgb( 231.0, 124.1, 21.0   )", opac_name: u"0.33"})
    assert_that(get_opac(), is_(0.33))
    assert_that(get_col(), is_("rgb(231.0,124.1,21.0)"))
    assert_that(get_ext(), is_("0.906 0.487 0.082 0.33"))

    # bad values don't change anything
    update_from_external_object(c, {col_name: u"rgb( 21.0, 18.1, F0   )"})
    assert_that(get_opac(), is_(0.33))
    assert_that(get_col(), is_("rgb(231.0,124.1,21.0)"))
