=================================================
RelStorage and Amazon Relational Database Service
=================================================

`RelStorage <http://pypi.python.org/pypi/RelStorage>`_ is a storage
implementation for ZODB that supports multiple clients through the use
of a SQL server. It is an alternative to ZEO. In addition to pushing
even more work out to individual clients instead of a central server
(conflict resolution is performed by each individual RelStorage
client, compared to in a single thread on a shared ZEO server for all
connected clients) it can use the underlying capabilities of of the
SQL server to handle replication, backups, and fault-tolerance.
Importantly, it also supports a history-free database, reducing the
need for storage space, packing, and garbage collection. Anecdotally,
it is usually faster than ZEO on top of a file storage.

Amazon's `Relational Database Service <http://aws.amazon.com/rds/>`_
(RDS) is a fully managed SQL service, supporting MySQL, Oracle, and SQL
Server. MySQL is free, the others are "bring your own license." (While
MySQL isn't much good as a database, it is just fine as a distributed
key-value store, which is basically what RelStorage needs.) Like the
other AWS services, RDS is pay-as-you-go, easy to work with (e.g., it
takes just a few clicks to set up database replicas, backups and
patches are automatic) and offers very easy scalability (e.g., one
command will increase the memory and processor cores of a database).

Together, RDS and RelStorage offer a compelling alternative to using a
dedicated machine for a ZEO server (or servers). RelStorage probably has better
scaling charecteristics, and RDS's hands-off management takes many of
the worries out of our hands. This document will provide a series of
notes about the process of setting up RelStorage and RDS in an EC2 instance.

Creating AWS Services
=====================

The first step is to create and configure the AWS services necessary
to support RelStorage. This consists of at least one RDS DB instance
running MySQL and one ElastiCache cluster (RelStorage uses Memcache
for improved efficiency and reduced database load; we could run our
own memcache server process on an existing EC2 instance since
RelStorage makes very limited demands, but it is anticipated that we
will make greater use of Memcache moving forward so getting experience
with ElastiCache makes sense).

Security
--------

Both of these services are "firewalled." Fortunately, it's very easy
to refer to existing EC2 security policies to provide access to the
required services by the designated machines (e.g., the "WebServer"
EC2 security policy is granted access to both the RDS and ElastiCache
instances created below.) Be very careful not to grant access outside
AWS or to machines that aren't ours; while it is possible to use IP
addresses in the security policy, it's best to refer to EC2 groups by name.

DB Instance
-----------

There's very little to creating an RDS DB instance. Simply choose an
instance size and name and create a user and initial database using
the wizard (we're using compute size and storage to stay within the
60-day free usage tier as of 2012-05-31). Use the latest version of
MySQL available and the standard port.

When the instance is created, it will be assigned a DNS name that you
can use to connect to it. Make a note of this.

Configuration
~~~~~~~~~~~~~

The MySQL instance needs to have its ``max_packet_size`` increased (we
used 64MB), as well as an increase in the number of possible
connections. This is done by creating and modifying a "DB Parameter
Group" to which the instance is assigned. This can only be done from
the command line. Fortunately, this is exactly the example given in
the documentation. (Note that the RDS command line tools are a
separate install from the normal AWS command line tools.)

It may also be helpful (to reduce MySQL 2006 warnings from RelStorage)
to set the ``wait_timeout`` value to an increased value (such as 600).

Finally, it is important to ensure that the ``max_connections`` value
is large enough. Each dataserver worker will need a number of
connections equal to the number of shards it is using (plus the root)
times the number of concurrent transactions it will handle. This
parameter should be at least 500.

Users and schemas
~~~~~~~~~~~~~~~~~

As part of the creation wizard, a MySQL user will be created. Although we
could use different users for each of the ZODB databases and MySQL
schemas, it's not clear there's a benefit, so we are currently just
using that one user.

Each ZODB database requires its own MySQL schema (one-to-one). Use the
``mysql`` command line to create these schemas. There is no further
initialization required, RelStorage handles it automatically.


ElastiCache
-----------

The Memcache setup is trivial. The only thing to do is to choose a
number and size of nodes (1 and small, currently) and then set up
firewall access. When the cluster (of one node) is ready, each node
will have a DNS name. Make a note of these.

EC2 Prerequisites
==================

``setup.py`` does not install RelStorage or its dependencies. They are
commented out in a block at the top of the file. Use pip to install
RelStorage, pylibmc, and MySQL-python.

Before installing the latter two, the native development packages must
be installed. ``yum`` can install the appropriate MySQL client
development package, but there is not an RPM for pylibmc's
``libmemcached`` dependency that is new enough (most recent RPM is
0.31 but 0.32 or better is required). Therefore, the simplest thing is
to compile and install the latest version of ``libmemcached`` from
source (``configure --prefix=/opt/nti && make install``). This build
requires C++ so it may be necessary to use ``yum`` to install
``gcc-c++`` first.

EC2 Environment Configuration
=============================

The ``nti_init_env`` command will create skeleton configurations for
everything needed by RelStorage; an existing environment can have
these files added by use of the ``--update_existing`` flag. If you
already have the ElastiCache and RDS instances ready, you can specify
them on the command line, otherwise you'll have to edit files in the
environment's ``etc`` directory::

	MYSQL_HOST=the_host MYSQL_CACHE=thecache:11211 MYSQL_USER=user MYSQL_PASSWD=pass nti_init_env /path/to/DsEnv config/development.ini --update_existing

The ``relstorage_conf.xml`` file contains the main configuration used
by the application and referred to from ``relstorage_uris.ini.`` When
ready (e.g., migration is complete), replace (symlink) ``zeo_uris.ini`` with
``relstorage_uris.ini`` (the dataserver only looks at
``zeo_uris.ini``). In addition to specifying the SQL database, this
config file contains many tunables described in the RelStorage
documentation. Here's a complete example::

	%import relstorage
	%import zc.zlibstorage

	<zodb Users>
		pool-size 7
		database-name Users
		<zlibstorage>
		<relstorage Users>
			blob-dir /opt/nti/DataserverEnv/data/data.fs.blobs
			shared-blob-dir false
			cache-servers zodb.wz3dwu.0001.use1.cache.amazonaws.com:11211
			cache-prefix Users
			poll-interval 0
			commit-lock-timeout 30
			keep-history false
			pack-gc false
			<mysql>
				db Users
				user ec2user
				passwd rdstemp001
				host alpharelstorage.cnv6nhiwf3j5.us-east-1.rds.amazonaws.com
			</mysql>
		</relstorage>
		<zlibstorage>
	</zodb>

Some notables: First, the relstorage is wrapped in ``zlibstorage`` to
dramatically improve cache efficiency and reduce database size and
network trafficy. Second, ``shared-blob-dir`` is set to false; for a
multi-dataserver-machine installation, it must be false (otherwise it
can be ommitted or set to true).

Migrating Existing Data
-----------------------

RelStorage comes with a ``zodbconvert`` command that can copy to and
from RelStorage and file/ZEO storages. (It is much faster to use raw
file storages). The ``nti_init_env`` script created migration
configurations for each database to copy from a file to RelStorage.
Simply point ``zodbconvert`` to one of these files to copy from a
local file to the SQL server (to use the file, ZEO cannot be running;
this is a good idea anyway to be sure that all databases are migrated in
a consistent state)::

	zodbconvert etc/zodbconvert_Search.xml

In one example, copying 5,500 transactions from a file to the smallest
RDS storage took 1.4 minutes. The process was network or IO bound as
neither the EC2 instance CPU nor the RDS instance CPU was saturated.
(Copying the other way is simply a matter of switching the ``source``
and ``destination`` names in the configuration file.)

It is convenient to reduce the number of transactions that must be
copied by running a `multi-database garbage collection
<http://pypi.python.org/pypi/zc.zodbdgc/>`_ and pack. A configuration
was created for this as well. It is a two-step process, first running
the multi-database GC (not a single-database GC, that could lose
objects) and then (optionally) packing each file. The following
command deletes the maximum number of objects with the most logging;
the process takes a few minutes::

	multi-zodb-gc -l DEBUG -d 0 etc/gc_conf.xml

There is also a configuration to do the same using ZEO (online), which
is much slower but requires no downtime. These same configurations can
be used with the ``multi-zodb-check-refs`` command; while it will
(eventually) generate a (large) file database containing the reference
tree if given the ``-r`` flag, it doesn't seem to actually find POSKeyErrors...


Operational Notes
=================

* RDS and ElastiCache are fully supported by CloudWatch (metrics) and
  nice pretty graphs are available in the AWS console.
* ``multi-zodb-gc`` does not work with RelStorage. However, packing
  and GC should be much less necessary since we are not preserving
  history.
* Eliminating the ZEO server frees up memory on the EC2 instance,
  memory that can be devoted to RelStorage caches.
* With a ``pool-size`` of 7, three databases, and 4 workers, the
  minimum number of MySQL connections consumed is 84.
* A ``commit-lock-timeout`` of 30 seconds is the default and seems
  reasonable.
* A ``poll-interval`` of 0 is the default and causes invalidation
  checks to be done every transaction. A larger value (e.g, 60) is
  more efficient if the database is read-mostly. With a value of 0,
  the cache is not used (?)
* Unfortunately, the default MySOL library is implemented in C and uses
  blocking IO, which means it doesn't play nicely with gunicorn and
  gevent (it prevents switching). We use an alternate driver that
  does play nicely by monkey-patching the system.
* The value of ``shared-blob-dir`` is critical; if false, there are
  other tunables (like ``blob-cache-size`` to consider).
