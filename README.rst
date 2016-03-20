DirectApps
==========

This is a little application for direct access to all the models and their
data in a project. By default, the application has access for users with
`is_staff` mark. But this and much more can be changed.

It might interest you if you use Django as the backend to some kind of
external client application. There are no templates for formatting and
displaying of data on the client. Only JSON. Only direct data. All quickly and
sharply.

.. note::
    The client application must support cookies, parse "csrftoken" and send
    it as `X-CSRFToken` header in `POST`, `PUT`, `PATCH` and `DELETE` requests.

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

Testing
-------

You can look at the example works in the JavaScript console and use it as a test.

.. code-block:: javascript

    function getCookie(cname) {
        var name = cname + "=";
        var ca = document.cookie.split(';');
        for(var i=0; i<ca.length; i++) {
            var c = ca[i];
            while (c.charAt(0)==' ') c = c.substring(1);
            if (c.indexOf(name) == 0) return c.substring(name.length,c.length);
        }
        return "";
    }

    function getResponse(method, url, data) {
        var xhr = new XMLHttpRequest();
        xhr.open(method, url, false);
        if (!(/^(GET|HEAD|OPTIONS|TRACE)$/.test(method.toUpperCase()))) {
            xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
        xhr.send(data);
        if (xhr.status == 200) return JSON.parse(xhr.responseText);
        console.error(xhr.responseText);
    }

    var group1 = getResponse('post', '/apps/auth/group/', 'name=Operators 1'),
        group2 = getResponse('post', '/apps/auth/group/', 'name=Operators 2');

    getResponse('get', '/apps/auth/group/?o=name,-id&q=operators&p=1&l=3&id__gte=1');
    getResponse('delete', '/apps/auth/group/', 'id='+group1.pk+','+group2.pk);


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

