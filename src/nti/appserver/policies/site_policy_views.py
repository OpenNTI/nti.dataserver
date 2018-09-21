#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contains views that do interesting or different things based on site policies.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class,no-value-for-parameter

import errno

from pyramid.interfaces import IView

from pyramid.view import view_config

from zope import component
from zope import interface

from nti.appserver import httpexceptions as hexc

from nti.appserver.interfaces import IApplicationSettings

from nti.appserver.policies import site_policies

logger = __import__('logging').getLogger(__name__)


class ISiteCSSMarker(interface.Interface):
    pass


@interface.implementer(ISiteCSSMarker)
class SiteCSSMarker(object):
    pass


class ISiteStringsMarker(interface.Interface):
    pass


@interface.implementer(ISiteStringsMarker)
class SiteStringsMarker(object):
    pass


class ISiteLandingMarker(interface.Interface):
    pass


@interface.implementer(ISiteLandingMarker)
class SiteLandingMarker(object):
    pass


@interface.implementer(IView)
class LegacyResourceView(object):
    """
    For moving off of the SiteXXXMarkers but not actually correctly
    using static views.
    """

    def __init__(self, site, name):
        self.site = site
        self.name = name

    def __call__(self, unused_context, request):
        new_path = request.path.split('/')[1:-1]  # the path to the directory
        new_path.append(self.site)
        new_path.append(self.name)
        return hexc.HTTPSeeOther(location=request.resource_path(request.context, *new_path))


def _response_for_site_resource_with_marker(marker_interface, request, resource, mime_type):
    """
    Searches for an :class:`.IView` utility having the given resource name
    and if found, hands control over to it.

    Currently, this is invoked within a sub-space of some other
    URL tree. Specific holes are punched in proxy forwarding rules
    to send exact URL matches (down to the file) through to the routes
    that call this function. Therefore, the view that is called cannot
    assume that it can return more than one file (e.g., no siblings
    can be referenced without also mapping them somehow into the other
    URL space). This is probably a FIXME: area (to map entire directories
    through to avoid needing to change multiple URL trees).

    Static Views
    ============

    To use pyramid's default static views, a site package should set
    up a directory that contains the exact paths to serve (e.g.,
    ``/login/resources/css/site.css``). For example, ``views.py``
    could live beside the directory ``assets`` containing the file
    ``resources/css/site.css``; then a call to
    :class:`pyramid.static.static_view` like ``static_view("assets")``
    would create a view that could be registered under the name
    ``site.css``.

    Redirects and CDNs
    ------------------

    Generally these resources are extremely cacheable and will not place a load
    on the dataserver. If it is desired to serve them from a CDN sometimes, however,
    a view callable can use a "static URL" request and redirect to that. In the above
    example, the view callable would return a redirect to
    ``request.static_url("my.package:assets/resources/css/site.css")``, and
    the environment would have configured a static view with this path pointing
    to the CDN: ``config.add_static_view( path="my.package:assets", name="//cdn.com/assets/")``
    (usually this would be done in a pyramid ZCML file)

    Legacy Documentation
    ====================
    Either redirects to a configured resource or returns an empty
    response with the give mimetype, based on the active sites. We
    should be registered as a view on a path to a CSS file, and we
    will return responses within the directory enclosing that css
    file.

    We look for a simple named utility based on the site and determine
    what to do based on its presence. We could probably simplify this
    to just redirecting unconditionally, but we might wind up getting
    lots of 404 responses which is ugly.
    """

    view = component.queryUtility(IView, name=resource)

    if view:
        # If the web root is not our usual default, and the path is under
        # the web root, fix it up.
        settings = component.getUtility(IApplicationSettings)
        web_root = settings.get('web_app_root', '/NextThoughtWebApp/')
        if web_root != '/NextThoughtWebApp/' and request.environ['PATH_INFO'].startswith(web_root):
            path_info = request.environ['PATH_INFO']
            request.environ['PATH_INFO'] = path_info.replace(web_root, '/NextThoughtWebApp/')
        return view(request.context, request)

    # Extra legacy support...these markers are DEPRECATED
    marker, site_name = site_policies.queryUtilityInSite(marker_interface,
                                                         request=request,
                                                         return_site_name=True)
    if marker:
        logger.warning("Site %s is still using legacy marker %s",
                       site_name, marker)
        return LegacyResourceView(site_name, resource)(request.context, request)

    # Nothing found
    request.response.content_type = mime_type
    request.response.text = u''
    return request.response


@view_config(route_name='logon.logon_css',
             request_method='GET')
@view_config(route_name='webapp.site_css',
             request_method='GET')
def site_css_view(request):
    """
    Returns a configure site specific css or an empty response.
    We should be registered as a view on a path to a CSS file, and
    we will return responses within the directory enclosing that css file.
    """
    return _response_for_site_resource_with_marker(ISiteCSSMarker, request, 'site.css', 'text/css')


@view_config(route_name="logon.strings_js",
             request_method='GET')
@view_config(route_name="webapp.strings_js",
             request_method='GET')
def webapp_strings_view(request):
    """
    Redirects to a site specific strings file based on the current site policy.
    """
    # The final part of the name of the path that matches this route
    # is 'site.js', but the resource we want to look for is actually 'strings.js',
    # This makes doing simple static redirections much harder than necessary and places
    # a lot of burden on specific implementations for sites.
    # Our hacky fix here is to adjust the PATH_INFO to reflect the desired name
    assert request.environ['PATH_INFO'].endswith('site.js')
    request.environ['PATH_INFO'] = request.environ['PATH_INFO'][:-7] + 'strings.js'

    return _response_for_site_resource_with_marker(ISiteStringsMarker,
                                                   request,
                                                   'strings.js',
                                                   'application/javascript')


_SITE_LANDING_COOKIE_NAME = 'nti.landing_site_name'


@view_config(route_name='landing.site_html',
             request_method='GET')
def landing_html_view(request):
    """
    Redirects to a site specific landing page if one exists in the
    current site policy. We do this by redirecting to last folder
    component of our path and setting a cookie for the site name. If
    this site policy doesn't have a landing page we redirect without
    the cookie.

    .. note: This can now go away; we are removing the use of this site and this cookie
            entirely, as it was redundant with the Host header. We can use that header
            in Nginx rules to check for files on disk at specified locations, using
            symlinks where necessary.
    """

    marker, site_name = site_policies.queryUtilityInSite(ISiteLandingMarker,
                                                         request=request,
                                                         return_site_name=True)

    # Send them a redirect to folder for this request (basically pop off the
    # last bit)
    new_path = request.path.split('/')[1:-1]

    response = hexc.HTTPSeeOther(location=request.resource_path(request.context,
                                                                *new_path,
                                                                query=request.params))
    if marker:
        # Live for 5 minutes.  We really just want this long enough to get
        # through the redirect
        response.set_cookie(_SITE_LANDING_COOKIE_NAME,
                            site_name.encode('utf-8'), 600)
    else:
        response.delete_cookie(_SITE_LANDING_COOKIE_NAME)

    return response


import os

from pyramid.path import caller_package

from pyramid.static import static_view

import scss


@interface.implementer(IView)
class _StaticView(static_view):

    assets_dir = None

    def __new__(cls, package, **kwargs):
        # Assuming this is broken out on the filesystem. Could use
        # pyramid's package stuff to handle that better

        _my_dir = os.path.dirname(package.__file__)
        _my_dir = os.path.abspath(_my_dir)
        assets_dir = os.path.join(_my_dir, 'assets')
        inst = super(_StaticView, cls).__new__(cls, assets_dir, **kwargs)
        inst.assets_dir = assets_dir
        return inst

    def __init__(self, unused_package, **kwargs):
        super(_StaticView, self).__init__(self.assets_dir, **kwargs)


@interface.named('strings.js')
class _StringsJsView(_StaticView):
    pass


@interface.named('site.css')
class _CompilingSCSSView(_StaticView):

    def __new__(cls, *args, **kwargs):  # pylint: disable=arguments-differ
        inst = super(_CompilingSCSSView, cls).__new__(cls, *args, **kwargs)

        _my_dir = inst.assets_dir

        _scss_dir = os.path.join(
            _my_dir, 'NextThoughtWebApp', 'resources', 'scss'
        )
        _css_dir = os.path.join(
            _my_dir, 'NextThoughtWebApp', 'resources', 'css'
        )
        _scss_file = os.path.join(_scss_dir, 'site.scss')
        _css_file = os.path.join(_css_dir, 'site.css')

        # Sadly, logging is ineffective at this time, we expect to be at the
        # module level
        if os.path.isfile(_scss_file) and os.stat(_scss_file).st_size:
            # Remove CSS if this file goes away/to zero bytes?
            if not os.path.isdir(_css_dir):
                try:
                    os.mkdir(_css_dir)
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        logger.warning(
                            "Error creating directory %s. Directory already exists.  Running unit tests concurrently?",
                             _css_dir)
                    else:
                        raise

            if 	   not os.path.isfile(_css_file) \
                or os.stat(_scss_file).st_mtime > os.stat(_css_file).st_mtime:
                compiler = scss.Scss(
                    scss_opts={'compress': False, 'debug_info': False}
                )
                with open(_scss_file, "r") as source:
                    scss_string = source.read()
                compiled = compiler.compile(scss_string=scss_string)
                with open(_css_file, 'w') as f:
                    f.write(compiled)
        return inst


def make_strings_view():
    """
    Return a view for strings.js, in the standard assets path.

    Register as a utility.
    """
    pack = caller_package()
    return _StringsJsView(pack)


def make_scss_view():
    """
    Return a view for the site CSS in the standard assets path.
    If the SCSS cannot compile, this will raise an exception.
    Empty and missing files are ignored.

    Register as a utility.
    """
    pack = caller_package()
    return _CompilingSCSSView(pack)
