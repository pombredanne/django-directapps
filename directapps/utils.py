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

def access(request):
    "Проверяет, является ли пользователь запроса сотрудником."
    return request.user.is_staff

def get_all_model_perms(model):
    "Возвращает итератор всех разрешений модели."
    meta = model._meta
    app_label = meta.app_label
    model_name = meta.model_name
    for p in meta.permissions:
        yield '%s.%s' % (app_label, p[0])
    for p in meta.default_permissions:
        yield '%s.%s_%s' % (app_label, p, model_name)

def get_model_perms(user, model):
    "Возвращает итератор всех разрешений, доступных пользователю."
    for p in get_all_model_perms(model):
        if user.has_perm(p):
            yield p

def has_model_perms(user, model):
    "Проверяет доступность модели для пользователя."
    for p in get_model_perms(user, model):
        return True
    return False

def is_m2m_layer(model):
    "Проверяет, является ли модель связкой для поля `ManyToManyField`."
    meta = model._meta
    fields = meta.fields
    if len(fields) == 3:
        f0, f1, f2 = fields
        if f1.rel and f2.rel:
            if f1.rel.one_to_many and f2.rel.one_to_many:
                return True
    return False

def serialize_field(f):
    "Сериализует поля моделей."
    data = {
        'name': f.name,
        'type': f.__class__.__name__, #get_internal_type(),
        'display_name': f.verbose_name,
        'editable': f.editable,
        'null': f.null,
        'blank': f.blank,
        'has_default': f.has_default(),
    }

    if f.max_length:
        data['max_length'] = f.max_length
    if f.description:
        data['description'] = f.description % data
    exclude_defaults = ('DateField', 'DateTimeField', 'TimeField')
    if f.has_default() and data['type'] not in exclude_defaults:
        data['initial'] = f.get_default()
    if f.help_text:
        data['help_text'] = f.help_text
    if f.choices:
        data['choices'] = f.get_choices(include_blank=False)
    if f.related_model:
        m = f.related_model._meta
        data['relation'] = '%s.%s' % (m.app_label, m.model_name)
    return data
