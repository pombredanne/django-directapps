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
from operator import or_ as OR

from django.db.models import Q
from django.shortcuts import _get_queryset

def smart_search(klass, fields, query):
    """
    Возвращает отфильтрованный набор данных.

    klass может быть Model, Manager, или объектом QuerySet. Если нет списка
    полей 'fields', либо нет строки поиска 'query', то возвращает набор как
    есть.
    """
    queryset = _get_queryset(klass)

    def construct_search(field_name):
        if field_name.startswith('^'):
            return "%s__istartswith" % field_name[1:]
        elif field_name.startswith('='):
            return "%s__iexact" % field_name[1:]
        elif field_name.startswith('@'):
            return "%s__search" % field_name[1:]
        else:
            return "%s__icontains" % field_name

    if fields:
        lookups = [construct_search(str(f)) for f in fields]
        if not query in ('', None, False, True):
            for bit in query.split():
                queries = [Q(**{lookup: bit}) for lookup in lookups]
                queryset = queryset.filter(reduce(OR, queries))

    return queryset


def get_object_or_none(klass, *args, **kwargs):
    """
    Возвращает объект или None, если объект не существует.

    klass может быть Model, Manager, или объектом QuerySet. Все остальные
    переданные параметры используются для запроса get().

    Замечание: Возвращает None, если найдено более одного объекта.
    """
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        return None
    except queryset.model.MultipleObjectsReturned:
        return None
