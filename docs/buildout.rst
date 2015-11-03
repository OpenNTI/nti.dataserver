==========
 Buildout
==========

As mentioned today at scrum, we'd like to begin the process of
deprecating the old-style monolithic dataserver packaging in favor of
the new, much more flexible, `buildout
<https://pypi.python.org/pypi/zc.buildout/>`_ based system. In this
note I'll document the process for switching local developer
environments. I think you should find the process pretty painless [1]_
and I think you'll enjoy the benefits of buildouts (such as no more
issues updating numpy and automatic-configuration updates).

For any questions or if you run into trouble, please email
ntiserverdev@nextthought.com or talk to one of us.


Prerequisites
=============

* python 2.7
* virtualenv and virtualenvwrapper (optional)

  Buildout works independently of virtual environments. Using a
  virtual environment with buildout can be very convenient, though,
  and since everyone already has it available (it being required under
  the old system) I'll write these instructions to use it.

  .. note:: Before you begin, make sure your virtualenv is up to date.
			Due to packaging changes in setuptools/distribute, older
			versions may have problems.

General
=======

Buildout is intended to be an advanced system for developing and
deploying complex applications in a repeatable fashion, handling the
lifecycle from initial development through deployments across multiple
different environments to maintenance of those environments as the
software changes. It vastly simplifies working with the many parts
that make up an application such as our own---it has the ability to
wire together the required components, create configuration files for
the components and things like haproxy and nginx, and it is easily
extensible.

Since its meant to be repeatable, buildout is all driven off of
configuration files using the typical ``.ini`` syntax. (Somewhat
confusingly, these files can also be referred to as "buildouts."). To
get started with buildout, you need only a python interpreter and a
buildout configuration file. Simplifying things even further,
configuration files are usually accompanied by a small
``bootstrap.py`` file that performs the necessary steps to get
buildout up and running. Again for repeatability purposes, these files
are usually checked into version control (together with any resources,
like templates, needed to configure the application).

Currently, our buildout configurations and bootstrap can be found at
``https://repos.nextthought.com/svn/nti-svn/NextThoughtPlatform/trunk/nti.dataserver-buildout``,
you'll need to check this directory out.

.. warning:: We use ``bootstrap.sh`` rather than ``bootstrap.py`` to
			 better handle changes in the version of ``setuptools``.
			 Without this script a change to ``setuptools`` requires
			 rebuilding everything. Watch for commit messages that change
			 the version of ``setuptools`` and tell you to rerun
			 ``bootstrap.sh`` and do so after updating to that version or
			 you will be in for a surprise.

Running ``bootstrap.sh`` creates the basic skeleton of an application
environment, including the ``bin/buildout`` script in the current
directory. (Somewhat more confusingly, the directory in which
``bootstrap.sh`` is run and which holds ``bin/buildout`` is also
sometimes called a buildout---think of it like an instance of a
class.) This script is then given a configuration file and takes care
of setting up and maintaining the application environment, including
checking out necessary code from source control, creating and updating
configuration files, etc.

Step-by-step
============

Buildout provides a lot of flexibility and options; this section will
outline one common workflow. Most people will want to use a simple
variation of this. This workflow creates one buildout (and hence one
"dataserver environment" or "DATASERVER_DIR") that can be updated.
It's easy to create and manage multiple buildouts; contact us for details.

Initial Setup
-------------

1. Create and activate a new virtual environment for use with buildout::

	 $ cd ~/Projects/
	 $ mkvirtualenv nti.dataserver-buildout
	 $ workon nti.dataserver-buildout

2. Checkout the buildout configurations::

	 $ export REPO=https://repos.nextthought.com/svn/nti-svn
	 $ svn co $REPO/NextThoughtPlatform/trunk/nti.dataserver-buildout

3. (Optional) The default locations for the content directory is
   relative to the buildout configuration. This lets one setup be used
   across machines for frontend and backend developers alike. To use
   these locations, checkout the projects (or move existing checkouts
   into place)::

	 $ mkdir DataserverGlobalLibrary
	 $ ls -F
	 nti.dataserver-buildout/
	 DataserverGlobalLibrary/

   Although the default locations for the webapp and login app are
   also relative to the buildout configuration, the production
   configuration and most developer configurations checkout these
   inside the buildout and adjust the configuration appropriately (see
   ``webapp.cfg``).

4. Bootstrap the buildout::

	 $ cd nti.dataserver-buildout
	 $ ./bootstrap.sh

This will generate some files and directories, notably the script
``bin/buildout``.

5. Install the buildout using the appropriate configuration. For most
   local development, this is currently
   ``developer_zeo_environment.cfg``; backend/server developers will
   want to use ``python_developer_environment.cfg`` (subject to
   change)::

	 $ bin/buildout -c developer_zeo_environment.cfg

The first thing this does is checkout all of the relevant source from
source control. Then it fetches their dependencies. It also creates a
bunch of directories and data files. This directory is now a
"buildout", and is also now a "dataserver environment";
``nti_init_env`` is no longer used.

In particular, scripts in the ``bin/`` directory, such as
``supervisord`` and ``pserve`` are preconfigured to use the settings
in this buildout. You no longer need to pass configuration files on
the command line.

Also, the ``parts/omelette`` directory is a convenient way to browse
(and grep/ack) all the source code used in the application.

This step can be lengthy; see the :ref:`tips-section` section for a
way to speed it up.

Running the Dataserver
----------------------

Simply startup supervisord:

  $ bin/supervisord -n

That runs all of the necessary elements in the foreground; stop them
all with Control-C or ``bin/supervisorctl shutdown``. This includes
HAProxy (on port 8082 by default) dispatching to Nginx for content and
of course the dataserver. For HTTPs testing, a self-signed SSL
endpoint exists on port 8443.

Updating
--------

To update your environment, performing the equivalent of what ``pip``
and ``setup.py`` were used for, as well as taking into account any
configuration changes required, simply re-run buildout::

  $ bin/buildout -c developer_zeo_environment.cfg

A powerful command called ``develop`` is installed in the buildout. It
can be used to simplify that command (remembering your configuration
file and options)::

  $ bin/develop rebuild
  Last used buildout arguments: -c python_developer_environment.cfg
  INFO: Running buildout.
  ...

The ``develop`` command is also used to automatically update all or a
subset of the code checked out::

  $ bin/develop up
  INFO: Queued 'nti.app.assessment' for update.
  INFO: Queued 'nti.app.client_preferences' for update.

See :ref:`develop-command` for more information.

Migrating An Existing Environment
=================================

If you have an existing local dataserver environment whose database
you'd like to preserve, that can be done simply by copying some files
from the old environment.

.. note:: This assumes your environment only had one database "shard"
		  named "Users" or "data"; most environments should only have
		  one shard. If you have more than one shard, contact us for
		  more information. You can tell if you have more than one
		  shard by counting the number of ``.fs`` files in the
		  ``data`` directory of the old environment. (There is a
		  pretty good chance that even if you have more shards, only
		  copying the main Users or data shard will still be
		  functional, so you can try that first.)

For every file and directory in the old ``data`` directory, there is a
corresponding file and directory in the new ``data`` directory.  The
idea is to copy the old files and directories into the new places. For
example::

  # Still in the new buildout directory as working directory
  $ export OLD_ENV=~/Projects/DsEnvs/DsEnv # My old environment
  $ ls -F $OLD_ENV
  data/  etc/  indicies/  var/
  $ ls -F $OLD_ENV/data # The old files
  data.fs  data.fs.blobs/  data.fs.index  data.fs.lock  data.fs.tmp
  $ ls -F data # So these are the new files
  Users.blobs/  Users.fs  Users.fs.index  Users.fs.lock  Users.fs.tmp

  # So I have one old shard named "data". I need to replace the
  # "Users" shard in the new buildout with the old files.

  $ cp $OLD_ENV/data/data.fs data/Users.fs
  $ cp $OLD_ENV/data/data.fs.index data/Users.fs.index
  $ rm -rf data/Users.blobs
  $ cp -R $OLD_ENV/data/data.fs.blobs data/Users.blobs

Differences
-----------

* Once you have bootstrapped the buildout, you are not required to
  continue to ``workon`` the virtual environment in the future as all
  the scripts in the ``bin`` directory explicitly refer to the correct
  dependencies. (However, this can be convenient, see the relevant tip.)

* ``bootstrap.sh`` and ``bin/buildout`` replace ``pip install -r
  requirements.txt``, ``setup.py`` and ``nti_init_env``

* ``supervisord_dev.conf`` no longer exists. Instead, just pass the
  ``-n`` argument to ``supervisord`` to run it in the console
  (foreground). You can control individual progroms and even restart
  just the ``pserve`` component to update dataserver code easily using
  the ``supervisorctl`` script::

    $ bin/supervisorctl restart pserve

* You *MUST NOT* edit the generated configuration files found in the
  ``etc/`` directory (as they will be overwritten next time you update
  the buildout). Instead, you need to provide arguments to the
  templates if you need to customize something. Contact us for more
  information.

.. _tips-section:

Tips
====

* Values in the buildout configuration files can be overridden or
  initially set using the user-specific configuration file found at
  ``~/.buildout/default.cfg``. Use this file to adjust template
  arguments, etc.

* Unlike with virtualenv, buildouts can safely and reliably share
  dependencies. This is done by causing the
  ``buildout:eggs-directory`` setting to point to a shared directory,
  one outside of any buildout or version control checkout (it defaults
  to the ``eggs`` directory of the buildout itself). The simplest way
  to do this is in your ``~/.buildout/default.cfg`` file. For
  example::

	[buildout]
	eggs-directory=/Users/jmadden/Projects/buildout-eggs
	download-cache=/Users/jmadden/Projects/buildout-cache

  You must use complete paths here, and the directories you specify
  must be created by hand. This is useful if you will have multiple
  buildouts, or if you anticipate wanting to re-create your main
  buildout (and database) from scratch. Set this before you run any
  ``buildout`` commands or you may find yourself downloading
  duplicates.

  This is especially useful with the next tip.

* To speed up the initial installation of the buildout and its
  dependencies, you may pre-populate the ``buildout:eggs-directory``.
  In production we may use mirror servers and local indexes, but the
  simplest thing to do in development is to copy the directory from
  someone else that already has it populated.

  You can also use the ``site-packages`` directory of the virtual
  environment you were previously using with ``nti.dataserver``. To do
  so, copy the contents of
  ``$VIRTUAL_ENV/lib/python2.7/site-packages`` to your eggs-directory,
  and then remove any ``.pth`` files, as well as any ``setuptools``
  eggs or directories. This may be expedient, but it results in an
  eggs-directory that is (possibly much) larger than it otherwise
  would be, and it may result in version conflicts. If you experience
  problems after trying this, start with a fresh eggs-directory.

* Because all the scripts in the ``bin`` directory automatically
  include their correct dependencies, you can add this directory to
  your $PATH without working on a virtual environment. For simple
  use-cases, you may want to simply do this directly in your shell
  startup scripts (e.g., ``~/.bash_profile``).

  For more complicated cases, you can automate the addition and
  removal of this path entry by connecting it to a virtual environment
  hook. That way, when you workon, activate, deactivate or switch
  between virtual environments the related buildout ``bin`` directory
  is added to the path. This is done by the creation of postactivate
  and postdeactivate hooks in the /virtual environments/ ``bin``
  directory (not the buildout's ``bin`` directory). These are
  executable shell scripts. For example::

	$ workon nti.dataserver-buildout
	$ cat $VIRTUAL_ENV/bin/postactivate
	export JM_VE_OLDPATH=$PATH
	PATH=~/Projects/NextThoughtPlatform/nti.dataserver-buildout/bin:$PATH
	$ cat $VIRTUAL_ENV/bin/postdeactivate
	PATH=$JM_VE_OLDPATH

* If you update your buildout checkout and/or recipe sources and then
  proceed to get a DistributionNotFound error from a recipe, the
  quickest fix is to re-bootstrap your buildout and then run the
  buildout command again::

	While:
	Installing.
	Getting section eggs.
	Initializing section eggs.
	Getting option eggs:initialization.
	Getting section environment.
	Initializing section environment.
	Getting option environment:smtp_passwd.
	Getting section passwords.
	Initializing section passwords.
	Loading zc.buildout recipe entry nti.recipes.passwords:default.

	An internal error occurred due to a bug in either zc.buildout or in a
	recipe being used:
	Traceback (most recent call last):
	...
	raise DistributionNotFound(req)
	DistributionNotFound: pycrypto>=2.6

	$ ./bootstrap.sh
	$ bin/bootstrap -c ....


Having Buildout Automatically Update Sources
--------------------------------------------

Running ``bin/buildout`` can automatically update checked out project
sources. This is not enabled by default for developers, but is for
production environments. To update sources at ``bin/buildout`` time,
supply the ``always-checkout`` argument::

    $ bin/buildout -c python_developer_environment.cfg buildout:always-checkout=true
    mr.developer: Queued 'NextThoughtLoginApp' for checkout.
    ...

Once you do this, the ``bin/devolop`` command remembers this setting::

    $ bin/develop rebuild
    Last used buildout arguments: -c python_developer_environment.cfg buildout:always-checkout=true
    INFO: Running buildout.
    mr.developer: Queued 'NextThoughtLoginApp' for checkout.
    ...

.. _develop-command:

The Develop Command
-------------------

The ``bin/develop`` command is a powerful command for simplifying many
aspects of working with buildout.

.. command-output:: develop --help


.. rubric:: Footnotes

.. [1] Despite what you may have seen at New Guy's desk today. That was
	   all him.
