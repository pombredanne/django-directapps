# -*- coding: utf-8 -*-
#
#   Copyright 2016 Grigoriy Kramarenko <root@rosix.ru>
#
#   This file is part of DirectApps.
#
#   DirectApps is free software: you can redistribute it and/or
#   modify it under the terms of the GNU Affero General Public License
#   as published by the Free Software Foundation, either version 3 of
#   the License, or (at your option) any later version.
#
#   DirectApps is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public
#   License along with DirectApps. If not, see
#   <http://www.gnu.org/licenses/>.
#

from django.conf.urls import url, include
from django.contrib.auth.views import login, logout

from directapps.views import director

rel_patterns = [
    url(r'^$', director, name='relation'),
    url(r'^_(?P<action>\w+)/$', director, name='relation_action'),
    url(r'^(?P<relation_object>\w+)/$', director, name='relation_object'),
    url(r'^(?P<relation_object>\w+)/_(?P<action>\w+)/$', director, name='relation_object_action'),
]

object_patterns = [
    url(r'^$', director, name='object'),
    url(r'^_(?P<action>\w+)/$', director, name='object_action'),
    url(r'^(?P<relation>\w+)/', include(rel_patterns)),
]

model_patterns = [
    url(r'^$', director, name='model'),
    url(r'^_(?P<action>\w+)/$', director, name='model_action'),
    url(r'^(?P<object>\w+)/', include(object_patterns)),
]

app_patterns = [
    url(r'^$', director, name='app'),
    url(r'^(?P<model>\w+)/', include(model_patterns)),
]

urlpatterns = [
    url(r'^$', director, name='apps'),
    url(r'^(?P<app>\w+)/', include(app_patterns)),
]

