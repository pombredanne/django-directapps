DirectApps
==========

This is a little application for direct access to all the models and their
data in a project. By default, the application has access for users with
`is_staff` mark. But this and much more can be changed.

It might interest you if you use Django as the backend to some kind of
external client application. There are no templates for formatting and
displaying of data on the client. Only JSON. Only direct data. All quickly and
sharply.


Installation
------------

.. code-block:: shell

    pip install django-directapps

Change your next project files.

.. code-block:: python

    # settins.py
    INSTALLED_APPS = (
        ...
        'directapps',
        ...
    )

    # urls.py
    urlpatterns = [
        ...
        url(r'^apps/', include('directapps.urls', namespace="directapps")),
        ...
    ]

Enjoy!

Settings
--------

All next settings must be within the dictionary `DIRECTAPPS`, when you
define them in the file settings.py

ATTRIBUTE_NAME
~~~~~~~~~~~~~~
The name of the attribute in the model that is bound to the controller.
By default is `directapps_controller`.

CONTROLLERS
~~~~~~~~~~~
Dictionary own controllers for models of third-party applications.
By default is blank.

EXCLUDE_APPS
~~~~~~~~~~~~
The list of excluded applications.
By default is blank.

EXCLUDE_MODELS
~~~~~~~~~~~~~~
The list of excluded models.
By default is blank.

ACCESS_FUNCTION
~~~~~~~~~~~~~~~
Function that checks access to pages.
By default is `None` and uses internal function.

JSON_DUMPS_PARAMS
~~~~~~~~~~~~~~~~~
The options for creating JSON.
By default is ``{'indent': 2, 'ensure_ascii': False}``.

