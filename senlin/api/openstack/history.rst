
API Version History
~~~~~~~~~~~~~~~~~~~

This document summarizes the changes made to the REST API with every bump of
API microversion. The description for each version should be verbose so that
it can be used by both users and developers.


1.1
---

   This is the initial version of the v1 API which supports microversions.
   The v1.1 API is identical to that of v1.0 except for the new supports to
   microversion checking.

   A user can specify a header in the API request::

     OpenStack-API-Version: clustering <version>

   where the ``<version>`` is any valid API version supported. If such a
   header is not provided, the API behaves as if a version request of v1.0
   is received.

1.2
---

   Added ``cluster_collect`` API.
