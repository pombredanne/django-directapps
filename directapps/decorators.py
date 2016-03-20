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

from __future__ import unicode_literals
from functools import wraps
from io import BytesIO

from django.http.request import QueryDict, MultiValueDict
from django.http.multipartparser import MultiPartParserError


def _load_post_and_files(request):
    """
    Заполняет `request._post` и `request._files`.

    Работает с методами 'PUT', 'PATCH' и 'DELETE' и только если тип
    контента является данными формы.
    """
    if request.method not in ('PUT', 'PATCH', 'DELETE'):
        return
    if request._read_started and not hasattr(request, '_body'):
        request._mark_post_parse_error()
        return

    update = bool(request.method != 'DELETE')

    if update and request.META.get('CONTENT_TYPE', '').startswith('multipart/form-data'):
        if hasattr(request, '_body'):
            # Use already read data
            data = BytesIO(request._body)
        else:
            data = request
        try:
            request._post, request._files = request.parse_file_upload(request.META, data)
        except MultiPartParserError:
            # An error occurred while parsing POST data. Since when
            # formatting the error the request handler might access
            # request.POST, set request._post and request._file to prevent
            # attempts to parse POST data again.
            # Mark that an error occurred. This allows request.__repr__ to
            # be explicit about it instead of simply representing an
            # empty POST
            request._mark_post_parse_error()
            raise
    elif request.META.get('CONTENT_TYPE', '').startswith('application/x-www-form-urlencoded'):
        request._post, request._files = QueryDict(request.body, encoding=request._encoding), MultiValueDict()
    else:
        request._post, request._files = QueryDict('', encoding=request._encoding), MultiValueDict()


def parse_rest(function=None):
    """
    Декоратор для представлений, использующих методы 'PUT', 'PATCH', 'DELETE'.

    Заполняет '_post и '_files аналогично тому, как это делает Django для
    метода 'POST' и делает доступными в атрибуте 'data' переданные данные
    (кроме файлов).
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not hasattr(request, 'data'):
                _load_post_and_files(request)
                if request.method == 'GET':
                    request.data = request.GET
                else:
                    request.data = request.POST
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    if function:
        return decorator(function)
    return decorator


