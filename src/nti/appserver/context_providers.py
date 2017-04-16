#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for exposing the content library to clients.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.appserver.interfaces import ForbiddenContextException
from nti.appserver.interfaces import IHierarchicalContextProvider
from nti.appserver.interfaces import ITopLevelContainerContextProvider
from nti.appserver.interfaces import ITrustedTopLevelContainerContextProvider


def _get_wrapped_contexts(top_level_contexts):
    results = []
    for context in top_level_contexts:
        try:
            results.append(context.ContentPackageBundle)
            results.extend(context.ContentPackageBundle.ContentPackages)
        except AttributeError:
            try:
                results.append(context.legacy_content_package)
            except AttributeError:
                try:
                    results.extend(context.ContentPackages)
                except AttributeError:
                    pass
    return results


def _dedupe_bundles(top_level_contexts):
    """
    Filter out bundles/packages that may be contained by other contexts.
    """
    results = []
    wrapped_bundles = _get_wrapped_contexts(top_level_contexts)
    for top_level_context in top_level_contexts:
        if top_level_context not in wrapped_bundles:
            results.append(top_level_context)
    return results


def get_top_level_contexts(obj):
    """
    Return all top-level contexts for a given object.
    """
    results = []
    for top_level_contexts in component.subscribers((obj,),
                                                    ITopLevelContainerContextProvider):
        if top_level_contexts:
            results.extend(top_level_contexts)
    return _dedupe_bundles(results)


def get_trusted_top_level_contexts(obj):
    """
    Return all top-level contexts for a given object, no matter
    the current state of such contexts.  Useful only for display
    purposes.
    """
    results = set()
    for top_level_contexts in component.subscribers((obj,),
                                                    ITrustedTopLevelContainerContextProvider):
        if top_level_contexts:
            results.update(top_level_contexts)
    return results


def get_top_level_contexts_for_user(obj, user):
    """
    Return all top-level contexts for a given object and user.
    """
    results = []
    for top_level_contexts in component.subscribers((obj, user),
                                                    ITopLevelContainerContextProvider):
        if top_level_contexts:
            results.extend(top_level_contexts)
    return _dedupe_bundles(results)


def _get_wrapped_bundles_from_hierarchy(hierarchy_contexts):
    """
    For our hierarchy paths, get all contained bundles.
    """
    top_level_contexts = (x[0] for x in hierarchy_contexts if x)
    return _get_wrapped_contexts(top_level_contexts)


def _dedupe_bundles_from_hierarchy(hierarchy_contexts):
    """
    Filter out bundles that may be contained by other contexts.
    """
    results = []
    wrapped_bundles = _get_wrapped_bundles_from_hierarchy(hierarchy_contexts)
    for hierarchy_context in hierarchy_contexts:
        # Make sure some provider didn't give us None.
        if hierarchy_context:
            top_level_context = hierarchy_context[0]
            if top_level_context not in wrapped_bundles:
                results.append(hierarchy_context)
    return results


def get_hierarchy_context(obj, user):
    """
    Return all hierarchical contexts for a given object and user.
    """
    results = []
    for hierarchy_contexts in component.subscribers((obj, user),
                                                    IHierarchicalContextProvider):
        if hierarchy_contexts:
            results.extend(hierarchy_contexts)
    return _dedupe_bundles_from_hierarchy(results)


def get_joinable_contexts(obj):
    """
    Return all joinable contexts for a given object.
    """
    results = set()
    try:
        get_top_level_contexts(obj)
    except ForbiddenContextException as e:
        results = set(e.joinable_contexts)
    return results
