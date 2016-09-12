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

from django.conf import settings

conf = getattr(settings, 'DIRECTAPPS', {})
ATTRIBUTE_NAME = conf.get('ATTRIBUTE_NAME', 'directapps_controller')
MASTER_CONTROLLER = conf.get('MASTER_CONTROLLER', None)
CONTROLLERS = conf.get('CONTROLLERS', {})
EXCLUDE_APPS = conf.get('EXCLUDE_APPS', ())
EXCLUDE_MODELS = conf.get('EXCLUDE_MODELS', ())
ACCESS_FUNCTION = conf.get('ACCESS_FUNCTION', None)
JSON_DUMPS_PARAMS = conf.get('JSON_DUMPS_PARAMS', {'indent': 2, 'ensure_ascii': False})
MASK_PASSWORD_FIELDS = conf.get('MASK_PASSWORD_FIELDS', True)
CHECKSUM_VERSION = conf.get('CHECKSUM_VERSION', '1')
# Стандарт 'ECMA-262' для JSON определяет передачу только милисекунд для
# объектов `datetime.datetime` и `datetime.time`. К тому же, он не позволяет
# передавать таймзону для `datetime.time`.
# Включите формат 'ISO', если все клиенты могут парсить полный формат времени,
# и это вам необходимо для бизнес-логики.
USE_TIME_ISOFORMAT = conf.get('USE_TIME_ISOFORMAT', False)

if ACCESS_FUNCTION:
    from django.utils.module_loading import import_string
    access = import_string(ACCESS_FUNCTION)
else:
    from directapps.utils import access


