#!/usr/bin/env bash

$VIRTUAL_ENV/bin/python `dirname $0`/bootstrap.py

# It is important that the version of setuptools we bootstrap against
# MATCHES the version listed in versions.cfg. If it does not, then we
# will wind up building things twice:

# The first time we run bin/buildout, it will install everything using
# the version of setuptools that we bootstrapped. As part of this
# process, the bin/buildout script is rewritten (because some egg
# depends on it?), and like all scripts written by buildout, it has
# the paths to the eggs specified in versions.cfg written into it. If
# that was a different setuptools version, than the
# __buildout_signature__ lines in .installed.cfg will no longer match,
# and the result is that next time bin/buildout is run, *everything*
# will get uninstalled and reinstalled. This cycle will repeat
# as long as the versions don't match.

# Because of that, it's important to keep versions.cfg current with
# the latest setuptools available. However, that in turn causes
# rebuilds simply due to the changing version.

# Fortunately, there aren't yet any bugs we've seen in setuptools that
# actually require reinstalling everything, especially not the C code.
# So when we change versions of setuptools, we also edit
# the .installed.cfg to match.

# First, extract the desired version:
setuptools_version=`grep -o "setuptools = .*" versions.cfg | grep -o "[0-9][0-9]\.[0-9].*"`
setuptools_egg="setuptools-$setuptools_version"

zc_buildout_version=`grep -o "zc.buildout = .*" versions.cfg | grep -o "[0-9]\.[0-9].*"`
zc_buildout_egg="zc.buildout-$zc_buildout_version"

collective_recipe_cmd_version=`grep -o "collective.recipe.cmd = .*" versions.cfg | grep -o "[0-9]\.[0-9].*"`
collective_recipe_cmd_egg="collective.recipe.cmd-$collective_recipe_cmd_version"

# Now match .installed.cfg with the desired version
if [ -f .installed.cfg ]; then
	case `uname` in
		Darwin)
			sed -E -i "" "s/setuptools-([0-9]\.?)+-/$setuptools_egg-/" .installed.cfg
			;;
		*)
			sed -E -i""  "s/setuptools-([0-9]\.?)+-/$setuptools_egg-/" .installed.cfg
			;;
	esac
	
	case `uname` in
		Darwin)
			sed -E -i "" "s/zc.buildout-([0-9]\.?)+-/$zc_buildout_egg-/" .installed.cfg
			;;
		*)
			sed -E -i""  "s/zc.buildout-([0-9]\.?)+-/$zc_buildout_egg-/" .installed.cfg
			;;
	esac
	
	case `uname` in
		Darwin)
			sed -E -i "" "s/collective.recipe.cmd-([0-9]\.?)+-/$collective_recipe_cmd_egg-/" .installed.cfg
			;;
		*)
			sed -E -i""  "s/collective.recipe.cmd-([0-9]\.?)+-/$collective_recipe_cmd_egg-/" .installed.cfg
			;;
	esac
fi

# If we bootstrapped to a different version, we cannot change it
# as the 'desired' egg may not actually exist...this is typically
# a developer bug with mismatched versions.cfg...best we can do is a
# warning
buildout_egg=`grep -o $setuptools_egg bin/buildout`
if [ "$buildout_egg" != "$setuptools_egg" ]; then
	RED="\033[0;31m"
	COLOR_NONE="\e[0m"

	buildout_egg=`grep -o setuptools-.*- bin/buildout`
	WARNING="Warning"
	echo -e "$RED$WARNING: setuptools bootstrapped ($buildout_egg) is different than versions.cfg ($setuptools_egg); expect rebuilds.$COLOR_NONE"
fi

buildout_egg=`grep -o $zc_buildout_egg bin/buildout`
if [ "$buildout_egg" != "$zc_buildout_egg" ]; then
	RED="\033[0;31m"
	COLOR_NONE="\e[0m"

	buildout_egg=`grep -o zc.buildout-.*- bin/buildout`
	WARNING="Warning"
	echo -e "$RED$WARNING: zc.buildout bootstrapped ($buildout_egg) is different than versions.cfg ($zc_buildout_egg); expect rebuilds.$COLOR_NONE"
fi
