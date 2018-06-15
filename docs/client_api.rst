===========
API Details
===========

NextThought provides a RESTful API for outside parties that need to interact with the platform in an automated fashion.  API endpoints are made available over a secure ssl connection (https).

.. note:: Insecure http endpoints are *NOT* available.

General
~~~~~~~

Environments
------------

NextThought makes available several production environments as well as several additional environments for development and integration testing.  Generally speaking there are 3 types of environments for every client.

* Alpha : Development and integration
* Test : Client acceptance and testing
* Production : Live production

Environment details for a given client integration will be provided at integration time.


Authentication
--------------

Authentication to secured APIs is provided using standard HTTP Basic Auth `RFC2617 <https://tools.ietf.org/html/rfc2617>`_.  Service account credentials for each integration and each environment will be provided at integration time.

.. note:: Unless otherwise noted all APIs require an authenticated request.

Identifier
----------

Either the NextThought username or the user"s external identifiers (the external_type and external_id) *MUST* be provided with all requests to the user update endpoints.  Failure to do so will result in an error being returned.

Requests
--------

Unless otherwise noted the `X-Requested-With: XMLHttpRequest` should be supplied with all requests.

Errors
------

Errors interacting with the API will be communicated using an appropriate `HTTP 4xx or 5xx response code <https://tools.ietf.org/html/rfc7231#section-6.5>`_. Some common error codes include:

 * `401 <https://tools.ietf.org/html/rfc7235#section-3.1>`_ : The endpoint requires authentication but no authentication information was supplied.
 * `403 <https://tools.ietf.org/html/rfc7231#section-6.5.3>`_ : The requesting user does not have access to the requested resource
 * `404 <https://tools.ietf.org/html/rfc7231#section-6.5.4>`_ : The endpoint being requested does not exist
 * 422 : The request is well-formed and syntactically correct but the body is semantically incorrect.  This may occur, for example, if a required parameter is not supplied.

Normal validation errors will come back as HTTP 4xx errors with a json body. This will
include a `message` and `code` fields. Unexpected, non-validation, errors may not return
with a json body.

Details
~~~~~~~

Specific API endpoints are found by traversing links on objects returned by the API. The entry point of the API is the *Service Document*.  The Service Doc consists of a set of Workspace objects which in turn contain a list of Collection and Link objects.

The service doc can be fetch with the following information.

HTTP Endpoint : /dataserver2/service

HTTP Method : GET

HTTP Response Code: 200 OK

HTTP Response Body: The service document

For the purposes of this integration we are interested in user objects and the `Global` and `Catalog` named workspaces.

The `Global` workspace will provide the `UserUpsert` API, the `ResolveUser` API, and the "UserInfoExtract" API. The `UserUpsert` result will contain the NextThought `username` field of the affected user. This NextThought `username` id can be used to `GrantAccess`/`RemoveAccess` and to retrieve `UserEnrollments`.

.. code-block:: javascript

 {"Class": "Workspace",
  "Items": [],
  "Links": [{"Class": "Link",
              "href": "/dataserver2/@@UserUpsert",
              "method": "POST",
              "rel": "UserUpsert"},
            {"Class": "Link",
              "href": "/dataserver2/ResolveUser",
              "rel": "ResolveUser"},
            {"Class": "Link",
              "href": "/dataserver2/UserInfoExtract",
              "rel": "UserInfoExtract"}],
  "Title": "Global"}

The `Catalog` workspace will include links for the GrantAccess and RemoveAccess APIs. The `Courses` collection within the `Catalog` workspace will contain the `ByTag` API for retrieving courses grouped by tags. These `CourseCatalogEntry` objects will contain `NTIID` identifier fields that can be used in the `GrantAccess`/`RemoveAccess` API.

.. code-block:: javascript

 {"Class": "Workspace",
  "Items": [{
              "Title": "Courses",
              "Class": "Collection",
              "href": "/dataserver2/users/josh.zuech@nextthought.com/Catalog/Courses",
              "Links": [{
                          "Class": "Link",
                          "href": "/dataserver2/users/josh.zuech@nextthought.com/Catalog/Courses/@@ByTag",
                          "rel": "ByTag"
                        }]
            }]
  "Links": [{"Class": "Link",
              "href": "/dataserver2/@@GrantAccess",
              "method": "POST",
              "rel": "GrantAccess"},
             {"Class": "Link",
              "href": "/dataserver2/@@RemoveAccess",
              "method": "POST",
              "rel": "RemoveAccess"}],
  "Title": "Catalog"}

The user object can be obtained as a result of the `UserUpsert` API or via the `ResolveUser` call. The user object will contain a `UserEnrollments` link that can be used to obtain the user enrollments. The absence of this link on the user object indicates the lack of enrollments.

.. code-block:: javascript

 {
   "Class": "User",
   "Username": "hazel",
   "Links": [{
               "Class": "Link",
               "href": "/dataserver2/users/hazel/@@UserEnrollments",
               "ntiid": "tag:nextthought.com,2011-10:system-NamedEntity:User-hazel",
               "rel": "UserEnrollments"
              }]
 }

 If a user object must be resolved from the external identifier fields (external_type and external_id), the `UserInfoExtract` API should be used. The `UserInfoExtract` API will take an HTTP Accept header defining the return type. The options are `text/csv` or `application/json`. A NextThought username can be retrieved that is mapped to an email address in the resulting data set. This username can then be used in the `ResolveUser` API.

 The `UserEnrollments` API will return a user"s enrollment records. The `CatalogEntryNTIID` value in these enrollment objects will map to NTIIDs found in the `ByTag` API and can be used in the `GrantAccess`/`RemoveAccess` APIs.

UserInfoExtract
---------------

The UserInfoExtract API allows for retrieving user metadata in the system, including finding a username for a specific email.

HTTP Endpoint: Global Workspace link object with rel=`UserInfoExtract`

HTTP Method: GET

HTTP Response Code:
 * 200 OK

HTTP Response Body: A json representation of user metadata

Example Request
===============

Example request url:
 * `http://localhost/dataserver2/@@UserInfoExtract`

Example request headers:

.. code-block:: javascript

 {
 "Authorization": "<redacted>",
 "Accept": "application/json",
 "Content-Length": "100",
 "Content-Type": "application/json",
 "Host": "localhost:80",
 "Origin": "http://mytest.nextthought.com",
 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/537.6 (KHTML, like Gecko) Chrome/23.0.1239.0 Safari/537.6",
 "X-Requested-With": "XMLHttpRequest"
 }

Example response json body:

.. code-block:: javascript

 {
    "Items": [
        {
            "alias": "Hazel",
            "createdTime": "2017-08-28T07:15:15.537293",
            "email": "hazel@gmail.com",
            "lastLoginTime": "2017-08-28T07:15:16.179477",
            "realname": "Hazel",
            "userid": "7150420170828",
            "username": "7150420170828",
            "external_ids": {
                              "employee_id": "123456",
                            },
        },
 }

ResolveUser
-----------

The ResolveUser API allows for retrieving users in the system.

HTTP Endpoint: Global Workspace link object with rel=`ResolveUser`

HTTP Method: GET

HTTP Response Code:
 * 200 OK

HTTP Response Body: A json representation of the user object

Example Request
===============

Example request url:
 * `http://localhost/dataserver2/ResolveUser/hazel`

Example request headers:

.. code-block:: javascript

 {
 "Authorization": "<redacted>",
 "Content-Length": "100",
 "Content-Type": "application/json",
 "Host": "localhost:80",
 "Origin": "http://mytest.nextthought.com",
 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/537.6 (KHTML, like Gecko) Chrome/23.0.1239.0 Safari/537.6",
 "X-Requested-With": "XMLHttpRequest"
 }

Example response json body:

.. code-block:: javascript

 {
   "Class": "User",
   "Username": "7150420170828",
   "external_ids": {
                     "employee_id": "123456",
                    },
   "Links": [{
               "Class": "Link",
               "href": "/dataserver2/users/7150420170828/@@UserEnrollments",
               "ntiid": "tag:nextthought.com,2011-10:system-NamedEntity:User-hazel",
               "rel": "UserEnrollments"
              }]
 }

UserEnrollments
---------------

The UserEnrollments API allows for retrieving user enrollents in the system. The `CatalogEntryNTIID` value in these enrollment objects will map to NTIIDs found in the `ByTag` API and can be used in the `GrantAccess`/`RemoveAccess` APIs.

HTTP Endpoint: user object link with rel=`UserEnrollments`

HTTP Method: GET

HTTP Response Code:
 * 200 OK

HTTP Response Body: A json representation of the user enrollments

Error Handling
==============

Here are some possible codes/messsages with the UserEnrollments operation:

* UserEnrollmentsNotFound - `User enrollments not found.`
    * This will return on a 404 if the user has no enrollments.
* CannotAccessUserEnrollmentsError - `Cannot view user enrollments.`
    * This would be if the calling user did not have permission to view enrollments.

Example Request
===============

Example request url:
 * `http://localhost/dataserver2/users/hazel/@@UserEnrollments`

Example request headers:

.. code-block:: javascript

 {
 "Authorization": "<redacted>",
 "Content-Length": "100",
 "Content-Type": "application/json",
 "Host": "localhost:80",
 "Origin": "http://mytest.nextthought.com",
 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/537.6 (KHTML, like Gecko) Chrome/23.0.1239.0 Safari/537.6",
 "X-Requested-With": "XMLHttpRequest"
 }

Example response json body:

.. code-block:: javascript

 {
    "Items": [
        {
            "CatalogEntryNTIID": "tag:nextthought.com,2011-10:NTI-CourseInfo-Alpha_NTI_Art",
            "Class": "CourseInstanceEnrollment",
            "CourseInstance": {
                "AdminLevel": "Alpha",
                "Class": "CourseInstance",
                "ContentPackageBundle": {
                    "Class": "ContentPackageBundle",
                    "ContentPackages": []
            }
        }
 }

ByTag
-----

The ByTag API allows for retrieving courses grouped by tag in the NextThought platform. Each tag will contain an `Items` collection of courses with the specified tag. These `CourseCatalogEntry` objects will contain an `NTIID` identifier field that can be used in the `GrantAccess`/`RemoveAccess` API.

HTTP Endpoint: Course Collection in the Catalog Workspace with a link object with rel=`ByTag`

HTTP Method: GET

HTTP Response Code:
 * 200 OK

HTTP Response Body: A json representation of the courses grouped by tag

Example Request
===============

Example request url:
 * `http://localhost/dataserver2/users/hazel/Catalog/Courses/@@ByTag`

Example request headers:

.. code-block:: javascript

 {
 "Authorization": "<redacted>",
 "Content-Length": "100",
 "Content-Type": "application/json",
 "Host": "localhost:80",
 "Origin": "http://mytest.nextthought.com",
 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/537.6 (KHTML, like Gecko) Chrome/23.0.1239.0 Safari/537.6",
 "X-Requested-With": "XMLHttpRequest"
 }

Example response json body:

.. code-block:: javascript

 {
 "Items": [
            { "Name": "art",
              "Items": [
                          { "Class": "CourseCatalogLegacyEntry",
                            "Description": "Introduction to Art",
                            "MimeType": "application/vnd.nextthought.courses.coursecataloglegacyentry",
                            "NTIID": "tag:nextthought.com,2011-10:NTI-CourseInfo-Alpha_NTI_Art",
                            "Title": "Introduction to Art",
                            "tags": ["art", "music"]
                          }
                       ]
            },
            { "Name": "music",
              "Items": [
                          { "Class": "CourseCatalogLegacyEntry",
                            "Description": "Course is for general education majors.",
                            "MimeType": "application/vnd.nextthought.courses.coursecataloglegacyentry",
                            "NTIID": "tag:nextthought.com,2011-10:NTI-CourseInfo-Alpha_NTI_Art",
                            "Title": "General Ed",
                            "tags": ["art", "music"]
                          },
                          { "Class": "CourseCatalogLegacyEntry",
                            "Description": "Introduction to music.",
                            "MimeType": "application/vnd.nextthought.courses.coursecataloglegacyentry",
                            "NTIID": "tag:nextthought.com,2011-10:NTI-CourseInfo-Alpha_NTI_Music",
                            "Title": "Music",
                            "tags": ["music"]
                          }
                       ]
            }
          ]
 }

UserUpsert
----------

The UserUpsert API allows for provisioning and/or updating user account information in the NextThought platform.

HTTP Endpoint: Global Workspace link object with rel=`UserUpsert`

HTTP Method: POST

HTTP Body: JSON object with the following fields

* `external_type` - the type of the external_id (e.g. `employee_id`)
* `external_id` - the user external_id
* `first_name` - (optional) the user"s first name, only used if no `real_name` provided.
* `last_name` - (optional) the user"s last name, only used if no `real_name` provided.
* `real_name` - (optional if first AND last name provided) the user"s real name. preferred to first and last
* `email` - (optional) the user"s email

HTTP Response Code:
 * 200 OK : The user upsert was applied

HTTP Response Body: A json representation of the user that was created

Error Handling
==============

Here are some possible codes/messsages with the UserUpsert operation:

* NoRealNameGiven - `Must provide real_name.`
* ExternalIdentifiersNotGivenError - `Must provide external_type and external_id.`
* CannotUpdateUserError - `Cannot update this user.`
    * This would be if the calling user did not have upsert permission.


Example Request
===============

Example request url:
 * `http://localhost/dataserver2/@@UserUpsert`

Example request headers:

.. code-block:: javascript

 {
 "Authorization": "<redacted>",
 "Content-Length": "100",
 "Content-Type": "application/json",
 "Host": "localhost:80",
 "Origin": "http://mytest.nextthought.com",
 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/537.6 (KHTML, like Gecko) Chrome/23.0.1239.0 Safari/537.6",
 "X-Requested-With": "XMLHttpRequest"
 }

Example request body:

.. code-block:: javascript

 {
 "external_type": "employee_id",
 "external_id": "123456",
 "email": "hazel-new@gmail.com",
 "real_name": "Hazel Izabel"
 }

Example response json body:

.. code-block:: javascript

 {
 "Class": "User",
 "ContainerId": "Users",
 "CreatedTime": 1501709564.714649,
 "Creator": "1041980252",
 "ID": "1041980252",
 "Links": [{"Class": "Link",
             "href": "/dataserver2/users/1041980252/Activity",
             "ntiid": "tag:nextthought.com,2011-10:system-NamedEntity:User-1041980252",
             "rel": "Activity"},
            {"Class": "Link",
             "href": "/dataserver2/users/1041980252/@@memberships",
             "ntiid": "tag:nextthought.com,2011-10:system-NamedEntity:User-1041980252",
             "rel": "memberships"},
            {"Class": "Link",
             "href": "/dataserver2/users/1041980252/SuggestedContacts",
             "ntiid": "tag:nextthought.com,2011-10:system-NamedEntity:User-1041980252",
             "rel": "SuggestedContacts"},
            {"Class": "Link",
             "href": "/dataserver2/users/1041980252/accept-invitations",
             "ntiid": "tag:nextthought.com,2011-10:system-NamedEntity:User-1041980252",
             "rel": "accept-invitations"},
            {"Class": "Link",
             "href": "/dataserver2/users/1041980252/Badges",
             "ntiid": "tag:nextthought.com,2011-10:system-NamedEntity:User-1041980252",
             "rel": "Badges"}],
 "MimeType": "application/vnd.nextthought.user",
 "NTIID": "tag:nextthought.com,2011-10:system-NamedEntity:User-1041980252",
 "NonI18NFirstName": null,
 "NonI18NLastName": null,
 "OID": "tag:nextthought.com,2011-10:1041980252-OID-0x2d99ca8e3f01ed40:5573657273:q1hPXH4NdPm",
 "Username": "1041980252",
 "about": null,
 "affiliation": null,
 "alias": "1041980252",
 "avatarURL": "https://secure.gravatar.com/avatar/854c35b2259699013ea995c78c57a9cf?s=128&d=identicon#using_provided_email_address",
 "backgroundURL": null,
 "containerId": "Users",
 "description": null,
 "education": null,
 "external_ids": {
                  "employee_id": "123456",
                 },
 "facebook": null,
 "googlePlus": null,
 "home_page": null,
 "href": "/dataserver2/users/1041980252",
 "interests": null,
 "lastLoginTime": 0,
 "linkedIn": null,
 "location": null,
 "positions": null,
 "realname": null,
 "role": null,
 "twitter": null
 }

GrantAccess
-----------

The GrantAccess API allows for the permissioning of resources in the NextThought platform.

HTTP Endpoint: Catalog Workspace link object with rel=`GrantAccess`

HTTP Method: POST

HTTP Body: JSON object with the following fields

* `external_type` - the type of the external_id (e.g. `employee_id`)
* `external_id` - the user external_id
* `ntiid` - the NextThought identifier for the resource that should be granted access (e.g. the CourseCatalogEntry NTIID field)
* `access_context` - an indication of why access is being granted to the user.  Currently the only supported value for this field is `PURCHASED`

HTTP Response Code:
 * 200 OK : Access was granted to the resource

HTTP Response Body: A json representation of resource access record

Error Handling
==============

Here are some possible codes/messsages with the GrantAccess operation:

* NoObjectIDGiven - `Must provide object to grant access to.`
* ObjectNotFoundError - `Object does not exist.`
* UserNotFoundError - `User not found.`
* ObjectNotAccessible - `Cannot grant access to object.`

Example Request
===============

Example request url:
 * `http://localhost/dataserver2/@@GrantAccess`

Example request headers:

.. code-block:: javascript

 {
 "Authorization": "<redacted>",
 "Content-Length": "143",
 "Content-Type": "application/json",
 "Host": "localhost:80",
 "Origin": "http://mytest.nextthought.com",
 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/537.6 (KHTML, like Gecko) Chrome/23.0.1239.0 Safari/537.6",
  "X-Requested-With": "XMLHttpRequest"
 }

Example request body:

.. code-block:: javascript

 {
 "external_type": "employee_id",
 "external_id": "123456",
 "ntiid": "tag:nextthought.com,2011-10:samplecourse-OID-0x02a09b1336a9c3e6:5573657273:muTnc9rffbs",
 }

Example response json body:

.. code-block:: javascript

 {
     "CatalogEntryNTIID": "tag:nextthought.com,2011-10:NTI-CourseInfo-ExampleCourse",
     "Class": "CourseInstanceEnrollment",
     "CreatedTime": 1509690802.449658,
     "LegacyEnrollmentStatus": "Open",
     "MimeType": "application/vnd.nextthought.courseware.courseinstanceenrollment",
     "NTIID": "tag:nextthought.com,2011-10:hazel-OID-0x1c1f42b3348e162e:5573657273:gqXvRFAxthu",
     "RealEnrollmentStatus": "Purchased",
     "Username": "1041980252"
 }

RemoveAccess
------------

The RemoveAccess API allows for removal of permissions of resources in the NextThought platform.

HTTP Endpoint: Catalog Workspace link object with rel=`RemoveAccess`

HTTP Method: POST

HTTP Body: JSON object with the following fields

* `external_type` - the type of the external_id (e.g. `employee_id`)
* `external_id` - the user external_id
* `ntiid` - the NextThought identifier for the resource that should be removed access

HTTP Response Code:
 * 200 OK : Access was removed from the resource

Error Handling
==============

Here are some possible codes/messsages with the RemoveAccess operation:

* NoObjectIDGiven - `Must provide object to grant access to.`
* ObjectNotFoundError - `Object does not exist.`
* UserNotFoundError - `User not found.`
* CannotRestrictAccess - `Cannot remove access to object.`

Example Request
===============

Example request url:
 * `http://localhost/dataserver2/@@RemoveAccess`

Example request headers:

.. code-block:: javascript

 {
 "Authorization": "<redacted>",
 "Content-Length": "143",
 "Content-Type": "application/json",
 "Host": "localhost:80",
 "Origin": "http://mytest.nextthought.com",
 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/537.6 (KHTML, like Gecko) Chrome/23.0.1239.0 Safari/537.6",
  "X-Requested-With": "XMLHttpRequest"
 }

Example request body:

.. code-block:: javascript

 {
 "external_type": "employee_id",
 "external_id": "123456",
 "ntiid": "tag:nextthought.com,2011-10:samplecourse-OID-0x02a09b1336a9c3e6:5573657273:muTnc9rffbs",
 }

