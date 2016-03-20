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
from datetime import datetime, date, time
from decimal import Decimal
from json import JSONEncoder as OrigJSONEncoder
from types import GeneratorType
from uuid import UUID

from django.utils.encoding import force_text
from django.utils.functional import Promise
from django.utils.timezone import is_aware


class JSONEncoder(OrigJSONEncoder):
    """
    Подкласс JSONEncoder, который умеет кодировать дату/время, числовой тип,
    генераторы, ленивые объекты перевода и исключения. Почти как в Django, но
    с дополнениями и чуть быстрее.
    """
    def default(self, o):
        # See "Date Time String Format" in the ECMA-262 specification.
        if isinstance(o, datetime):
            r = o.isoformat()
            if o.microsecond:
                r = r[:23] + r[26:]
            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'
            return r
        elif isinstance(o, date):
            return o.isoformat()
        elif isinstance(o, time):
            if is_aware(o):
                raise ValueError("JSON can't represent timezone-aware times.")
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        elif isinstance(o, Decimal):
            return str(o)
        elif isinstance(o, UUID):
            return str(o)
        elif isinstance(o, Exception):
            return force_text(o)
        elif isinstance(o, Promise):
            return force_text(o)
        elif isinstance(o, GeneratorType):
            return list(o)
        else:
            return super(JSONEncoder, self).default(o)


