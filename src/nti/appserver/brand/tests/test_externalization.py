#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_entries
from hamcrest import assert_that
from hamcrest import has_properties

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.testing.matchers import verifiably_provides

from nti.appserver.brand.model import SiteBrand
from nti.appserver.brand.model import SiteBrandImage
from nti.appserver.brand.model import SiteBrandAssets

from nti.appserver.brand.interfaces import ISiteBrand
from nti.appserver.brand.interfaces import ISiteBrandImage
from nti.appserver.brand.interfaces import ISiteBrandAssets

from nti.contentlibrary.zodb import PersistentHierarchyKey
from nti.contentlibrary.zodb import PersistentHierarchyBucket

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

CLASS = StandardExternalFields.CLASS
MIMETYPE = StandardExternalFields.MIMETYPE
CREATED_TIME = StandardExternalFields.CREATED_TIME
LAST_MODIFIED = StandardExternalFields.LAST_MODIFIED


class TestExternalization(ApplicationLayerTest):

    def test_brand(self):
        image_url = 'https://s3.amazonaws.com/content.nextthought.com/images/ifsta/reportassets/elibrary-image.jpg'
        bucket_path = u'bucket_site_name'
        bucket = PersistentHierarchyBucket(name=bucket_path)
        key = PersistentHierarchyKey(name=u'logo', bucket=bucket)
        logo_image = SiteBrandImage(source='file:///content/path/web.png',
                                    filename=u'filename.png',
                                    key=key)
        icon_image = SiteBrandImage(source='file:///content/path/icon')
        full_logo_image = SiteBrandImage(source=image_url)
        site_brand_assets = SiteBrandAssets(logo=logo_image,
                                            full_logo=full_logo_image,
                                            icon=icon_image,
                                            root=bucket)
        logo_image.__parent__ = site_brand_assets
        theme = {'a': 'aval',
                 'b': {'b1': 'b1val'},
                 'c': None}
        color = u'#404040'
        site_brand = SiteBrand(brand_name=u'brand name',
                               brand_color=color,
                               assets=site_brand_assets)
        site_brand._theme = theme

        assert_that(logo_image,
                    verifiably_provides(ISiteBrandImage))
        assert_that(icon_image,
                    verifiably_provides(ISiteBrandImage))
        assert_that(full_logo_image,
                    verifiably_provides(ISiteBrandImage))
        assert_that(site_brand_assets,
                    verifiably_provides(ISiteBrandAssets))
        assert_that(site_brand,
                    verifiably_provides(ISiteBrand))

        ext_obj = to_external_object(site_brand)
        assert_that(ext_obj[CLASS], is_('SiteBrand'))
        assert_that(ext_obj[MIMETYPE],
                    is_(SiteBrand.mime_type))
        assert_that(ext_obj[CREATED_TIME], not_none())
        assert_that(ext_obj[LAST_MODIFIED], not_none())
        assert_that(ext_obj['theme'], has_entries(**theme))

        assets = ext_obj.get('assets')
        assert_that(assets, not_none())
        assert_that(assets[CLASS], is_('SiteBrandAssets'))
        assert_that(assets[MIMETYPE],
                    is_(SiteBrandAssets.mime_type))
        assert_that(assets[CREATED_TIME], not_none())
        assert_that(assets[LAST_MODIFIED], not_none())

        logo = assets.get('logo')
        assert_that(logo, not_none())
        assert_that(logo[CLASS], is_('SiteBrandImage'))
        assert_that(logo[MIMETYPE],
                    is_(SiteBrandImage.mime_type))
        assert_that(logo[LAST_MODIFIED], not_none())
        assert_that(logo['source'], is_(logo_image.source))
        assert_that(logo['filename'], is_(u'filename.png'))
        assert_that(logo['href'], is_(u'/site-assets/logo'))

        full_logo = assets.get('full_logo')
        assert_that(full_logo, not_none())
        assert_that(full_logo[CLASS], is_('SiteBrandImage'))
        assert_that(full_logo[MIMETYPE],
                    is_(SiteBrandImage.mime_type))
        assert_that(full_logo[CREATED_TIME], not_none())
        assert_that(full_logo[LAST_MODIFIED], not_none())
        assert_that(full_logo['source'], is_(full_logo_image.source))
        assert_that(full_logo['filename'], none())

        icon = assets.get('icon')
        assert_that(icon, not_none())
        assert_that(icon[CLASS], is_('SiteBrandImage'))
        assert_that(icon[MIMETYPE],
                    is_(SiteBrandImage.mime_type))
        assert_that(icon[CREATED_TIME], not_none())
        assert_that(icon[LAST_MODIFIED], not_none())
        assert_that(icon['source'], is_(icon_image.source))
        assert_that(icon['filename'], none())

        # Logo props are not copied to other empty image fields
        for attr in ('email', 'favicon'):
            attr_ext = assets.get(attr)
            assert_that(attr_ext, none(), attr)

        factory = find_factory_for(ext_obj)
        assert_that(factory, not_none())
        new_io = factory()
        update_from_external_object(new_io, ext_obj, require_updater=True)
        assert_that(new_io, has_properties("brand_name", "brand name",
                                           'brand_color', color,
                                           "theme", has_entries(**theme),
                                           "assets", has_properties("logo",
                                                                    has_properties("source", is_(logo_image.source),
                                                                                   "filename", is_(logo_image.filename)),
                                                                    "full_logo",
                                                                    has_properties("source", is_(full_logo_image.source)),
                                                                    "icon",
                                                                    has_properties("source", is_(icon_image.source),
                                                                                   "filename", none()))))
