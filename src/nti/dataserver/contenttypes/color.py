#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contenttypes and properties related to working with colors.


When storing a color value, the RGBA colorspace is preferred.
This can be stored as a sequence of four floats between 0.0 and 1.0: [R, G, B, A].
This can be represented for external clients as both a string of those
four floating point numbers::

	1.0, 1.0, 0.9, 0.5

Or in CSS syntax::

	rgb(255, 255, 230)


Note that the CSS value is missing the opacity, so a secondary property is required
to externalize it::

   0.5

Altogether, this might look like::

   'fillRGBAColor': '1.000 1.000 1.000 0.00',
   'fillColor': 'rgb(255.0,255.0,255.0)',
   'fillOpacity': 0.0,


.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import operator


def _update_from_rgb_opacity(parsed, arr, colName, opacName):
    stroke_color = parsed.pop(colName, None)  # "rgb(r,g,b)"
    stroke_opacity = parsed.pop(opacName, None)  # float
    if stroke_color:
        try:
            r, g, b = map(float, stroke_color.strip()[4:-1].split(','))
        except ValueError:
            logger.warn("Bad data for %s: %s", colName, stroke_color)
        else:
            assert 0.0 <= r <= 255.0
            assert 0.0 <= g <= 255.0
            assert 0.0 <= b <= 255.0
            arr[0], arr[1], arr[2] = r / 255.0, g / 255.0, b / 255.0

    if stroke_opacity is not None:
        stroke_opacity = float(stroke_opacity)  # accept either string or float
        assert 0.0 <= stroke_opacity <= 1.0
        # opacity and alpha are exactly the same,
        # 0.0 fully transparent, 1.0 fully opaque
        arr[3] = stroke_opacity


def _update_from_rgba(arr, string, alpha=1.0):
    """
    A missing alpha value is assumed to mean 1.0, matching what happens
    with Omni's OQColor.
    """
    string = string.strip()
    string = string.lower()
    if string.startswith('rgba('):
        logger.warn("Bad data for RGBA: %s", string)
        string = string.strip()[5:-1].split(',')
        string = ' '.join(string)
    rgba = string.split(' ')
    if len(rgba) == 3:
        rgba = list(rgba)
        rgba.append(alpha)

    r, g, b, a = map(float, rgba)
    assert 0.0 <= r <= 1.0
    assert 0.0 <= g <= 1.0
    assert 0.0 <= b <= 1.0

    arr[0], arr[1], arr[2] = r, g, b
    assert 0.0 <= a <= 1.0

    arr[3] = a


def _write_rgba(val):
    if val[3] == 1.0:  # Comparing with a constant
        fs = "{:.3f} {:.3f} {:.3f}"
        val = val[0:3]
    else:
        fs = "{:.3f} {:.3f} {:.3f} {:.2f}"
    return fs.format(*val)


def _names(color_name):
    name = str(color_name)

    array_name = str('_' + name + '_rgba')

    prop_name = str(name + 'Color')
    prop_rgba_name = str(name + 'RGBAColor')
    prop_opac_name = str(name + 'Opacity')

    return array_name, prop_name, prop_rgba_name, prop_opac_name


def createColorProperty(color_name, r=1.0, g=1.0, b=1.0, opacity=1.0):
    """
    A class-level callable that installs the code necessary to
    support a color property as defined in this module.

    The class will get both a storage slot and three readable
    properties. For example, given the name ``fill``,
    you will get::

            _fill_rgba = (1.0, 1.0, 1.0, 1.0)
            @property
            def fillRGBAColor(self): ...
            @property
            def fillColor(self): ...
            @property
            def fillOpacity(self): ...

    """
    frame = sys._getframe(1)

    array_name, prop_name, prop_rgba_name, prop_opac_name = _names(color_name)

    getter = operator.attrgetter(array_name)

    def as_rgb(self):
        arr = getter(self)
        return "rgb({:.1f},{:.1f},{:.1f})".format(*[x * 255.0 for x in arr[0:3]])

    prop = property(as_rgb)

    def as_rgba(self):
        arr = getter(self)
        return _write_rgba(arr)

    prop_rgba = property(as_rgba)

    prop_opac = property(lambda self: getter(self)[3])

    frame.f_locals[array_name] = (r, g, b, opacity)
    frame.f_locals[prop_name] = prop
    frame.f_locals[prop_rgba_name] = prop_rgba
    frame.f_locals[prop_opac_name] = prop_opac


def updateColorFromExternalValue(self, color_name, parsed):
    """
    Given a color name that was created as a set of properties
    by :func:`createColorProperty`, update from an external dictionary
    that can contain either the RGBAColor value (preferred), or
    the rgb and (optional) opacity values.

    Modifies the parsed data to not have any of the color values.
    """

    array_name, prop_name, prop_rgba_name, prop_opac_name = _names(color_name)

    rgba_string = parsed.pop(prop_rgba_name, None)

    arr = list(getattr(self, array_name))
    orig = list(arr)

    if rgba_string:  # this takes precedence
        _update_from_rgba(arr, rgba_string)
        parsed.pop(prop_name, None)
        parsed.pop(prop_opac_name, None)
    else:
        _update_from_rgb_opacity(parsed, arr, prop_name, prop_opac_name)

    if arr != orig:
        setattr(self, array_name, tuple(arr))

    assert prop_name not in parsed
    assert prop_rgba_name not in parsed
    assert prop_opac_name not in parsed
