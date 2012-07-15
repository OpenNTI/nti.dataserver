from zope import component
from zope.configuration import xmlconfig

import nti.dataserver as dataserver
import nti.contentsearch as contentsearch
import nti.contentfragments as contentfragments
from nti.dataserver.tests.mock_dataserver import ConfiguringTestBase as DSConfiguringTestBase

phrases = (	"Yellow brown", "Blue red green render purple?",
			"Alpha beta", "Gamma delta epsilon omega.",
			"One two", "Three rendered four five.",
			"Quick went", "Every red town.",
			"Yellow uptown",  "Interest rendering outer photo!",
			"Preserving extreme", "Chicken hacker")

domain = (	"alfa", "bravo", "charlie", "delta", "echo", "foxtrot",
			"golf", "hotel", "india", "juliet", "kilo", "lima", "mike",
			"november", "oscar", "papa", "quebec", "romeo", "sierra",
			"tango", "uniform", "victor", "whiskey", "xray", "yankee",
			"zulu")

zanpakuto_commands =  (	"Shoot To Kill",
						"Bloom, Split and Deviate",
						"Rankle the Seas and the Skies",
						"Lightning Flash Flame Shell",
						"Flower Wind Rage and Flower God Roar, Heavenly Wind Rage and Heavenly Demon Sneer",
						"All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade",
						"Cry, Raise Your Head, Rain Without end",
						"Sting All Enemies To Death",
						"Reduce All Creation to Ash",
						"Sit Upon the Frozen Heavens",
						"Call forth the Twilight")


class ConfiguringTestBase(DSConfiguringTestBase):
	set_up_packages = (dataserver, contentsearch)
