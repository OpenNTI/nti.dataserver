#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, is_

from nti.utils import create_gravatar_url

def test_create_gravatar_url():
	assert_that( create_gravatar_url( 'jason.madden@nextthought.com' ),
				 is_( 'http://www.gravatar.com/avatar/5738739998b683ac8fe23a61c32bb5a0?s=128&d=mm' ) )

	assert_that( create_gravatar_url( 'jason.madden@nextthought.com', secure=True ),
				 is_( 'https://secure.gravatar.com/avatar/5738739998b683ac8fe23a61c32bb5a0?s=128&d=mm' ) )


	assert_that( create_gravatar_url( 'jason.madden@nextthought.com', defaultGravatarType='wavatar' ),
				 is_( 'http://www.gravatar.com/avatar/5738739998b683ac8fe23a61c32bb5a0?s=128&d=wavatar' ) )


	assert_that( create_gravatar_url( 'jason.madden@nextthought.com', size=512 ),
				 is_( 'http://www.gravatar.com/avatar/5738739998b683ac8fe23a61c32bb5a0?s=512&d=mm' ) )
