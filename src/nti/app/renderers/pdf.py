#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF response rendering, based on :mod:`z3c.rml`.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from z3c.rml import rml2pdf

from pyramid_chameleon.renderer import template_renderer_factory

from pyramid.interfaces import IRenderer
from pyramid.interfaces import IRendererFactory

from nti.app.pyramid_zope.z3c_zpt import ZPTTemplateRenderer

from nti.app.renderers.renderers import AbstractCachingRenderer


@interface.provider(IRendererFactory)
@interface.implementer(IRenderer)
def PDFRendererFactory(info):
    """
    A renderer that creates a PDF given an /asset specification/ or absolute
    path to an RML template.
    """

    # We use pyramid_chameleon's implementation to find asset files,
    # support overrides, etc, as well as caching implementation objects.
    return template_renderer_factory(info, _PDFRMLRenderer)


# pylint: disable=W0223,I0011


class _PDFRMLRenderer(AbstractCachingRenderer):

    def __init__(self, path, lookup, macro=None):
        self.zpt_renderer = ZPTTemplateRenderer(path, lookup, macro=macro)

    def _render_to_pdf(self, value, system):
        rml = self.zpt_renderer(value, system)
        # TODO: Probably need to set headers for forcing inline view vs download?
        # TODO: Filename
        pdf_stream = rml2pdf.parseString(rml)
        system['request'].response.content_type = str('application/pdf')
        return pdf_stream.read()

    _render_to_browser = _render_to_non_browser = _render_to_pdf
