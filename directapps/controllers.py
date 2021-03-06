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
import weakref

from django.contrib.auth.hashers import mask_hash
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.db.models import Q, Model, Manager
from django.db.models.fields import CharField
from django.db.models.fields.files import FieldFile
from django.db.models.lookups import default_lookups
from django.forms.models import modelform_factory
from django.utils.encoding import force_text
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _

from directapps.conf import (MASTER_CONTROLLER, CONTROLLERS,
    ATTRIBUTE_NAME, MASK_PASSWORD_FIELDS)
from directapps.exceptions import ValidationError, NotExistError
from directapps.shortcuts import smart_search
from directapps.utils import serialize_field, join_display_names_lazy

LOOKUPS_KEYS = default_lookups.keys()


class BaseController(object):
    """
    Базовый класс контролеров, которые непосредственно работают с моделями,
    менеджерами и полями моделей.

    Включает несколько реализованных действий:

    1. `scheme` - возвращает схему контроллера;
    2. `defaults` - возвращает значения по-умолчанию для полей объектов модели.
    3. `create` - создаёт один объект модели (синоним: `action_post`).
    4. `update` - обновляет один или более объектов модели
       (синонимы: `action_put` и `action_patch`).
    5. `delete` - удаляет один или более объектов модели.

    """
    valid_actions = {
        'get'   : ('GET',),
        'post'  : ('POST',),
        'create': ('POST',),
        'add'   : ('POST',),
        'put'   : ('POST', 'PUT'),
        'patch' : ('POST', 'PATCH'),
        'update': ('POST', 'PUT', 'PATCH'),
        'delete': ('POST', 'DELETE'),
        # прочие действия можно любым методом, даже 'GET'
    }
    exclude_fields = () # список полей, которые следует пропустить при
                        # формировании контроллеров
    select_related = None # определяет связанные объекты, которые нужно
                          # получить полностью за запрос, если нужно
                          # запретить это, то ставить False
    prefetch_related = None # определяет список m2m полей, которые нужно
                            # получить за раз, дополнительно к запросу,
                            # если нужно запретить это, то ставить False
    queryset_filters = None # словарь фильтров, которые всегда добавляются
                            # к QuerySet в методе get_queryset()
    search_key  = 'q' # ключ, по которому принимаются данные для поиска
    foreign_key = 'f' # ключ, по которому с клиента принимается имя поля или
                      # колонки с внешним соединением (для действия "_fkey")

    def __init__(self, model_or_manager, **kwargs):
        """Инициализация с помощью менеджера модели."""
        if isinstance(model_or_manager, Manager):
            self.manager = model_or_manager
            self.model   = self.manager.model
        else:
            self.model   = model_or_manager
            self.manager = self.model._default_manager

        meta = self.model._meta
        app_label  = meta.app_label
        model_name = meta.model_name
        self.add_perm    = '%s.add_%s'    % (app_label, model_name)
        self.change_perm = '%s.change_%s' % (app_label, model_name)
        self.delete_perm = '%s.delete_%s' % (app_label, model_name)

        all = [f for f in meta.fields if f.name not in self.exclude_fields]
        if meta.many_to_many:
            all.extend([f for f in meta.many_to_many \
                                if f.name not in self.exclude_fields])

        self.all_fields = all
        self.all_fields_names = [f.name for f in all]

        self.visible_fields = [f for f in all if not f.hidden]
        self.default_fields = [f for f in all if f.has_default()]
        self.editable_fields = [f for f in self.visible_fields if f.editable]
        self.editable_fields_names = [f.name for f in self.editable_fields]

        if self.select_related is None:
            self.select_related = [f.name for f in meta.fields \
                                        if f.name not in self.exclude_fields \
                                        and f.related_model]
        if self.prefetch_related is None:
            self.prefetch_related = [f.name for f in meta.many_to_many \
                                        if f.name not in self.exclude_fields]

    def get_queryset(self, request, **kwargs):
        qs = self.manager.all()
        if self.queryset_filters:
            qs = qs.filter(**self.queryset_filters)
        return qs

    def render_field(self, request, obj, field):
        """Рендерит поле объекта модели."""
        if '.' in field:
            data = obj
            for part in field.split('.'):
                if data is None:
                    break
                data = getattr(data, part, None)
            field = part
        else:
            data = getattr(obj, field, None)
        if MASK_PASSWORD_FIELDS and field == 'password' and data:
            return mask_hash(data)
        if isinstance(data, FieldFile):
            if data.name:
                return data.url
            return None
        elif isinstance(data, Model):
            return [data.pk, force_text(data)]
        elif isinstance(data, Manager):
            return [(i.pk, force_text(i)) for i in data.all()]
        return data

    def render_objects(self, request, qs):
        """Рендерит весь полученный QuerySet."""
        render = self.render_field
        fields = self.all_fields_names
        meta = self.model._meta
        app_label = meta.app_label
        model_name = meta.model_name
        def serialize(o):
            reverse_args = (app_label, model_name, o.pk)
            return {
                'fields': {f: render(request, o, f) for f in fields},
                'pk': o.pk,
                'display_name': force_text(o),
                'url': reverse('directapps:object', args=reverse_args)
            }
        return map(serialize, qs)

    def get_list_id(self, request, object=None, relation_object=None, rasing=True, **kwargs):
        """Возвращает список идентификаторов из запроса."""
        if object:
            list_id = [object]
        elif relation_object:
            list_id = [relation_object]
        else:
            list_id = request.data.get('id')
            if not list_id:
                if rasing:
                    raise ValidationError(_('The request body does not contain the list id.'))
                else:
                    return None
            list_id = list_id.split(',')
        return list_id

    def get_model_form(self, request, fields=None, **kwargs):
        if not fields:
            fields = self.editable_fields_names
        else:
            fields = [f for f in self.editable_fields_names if f in fields]
        if not fields:
            raise ValidationError(_('Not contains fields for object.'))
        kw = {}
        if hasattr(self, 'form'):
            kw['form'] = self.form
        return modelform_factory(self.model, fields=fields, **kw)

    def get_scheme(self, request, **kwargs):
        return 'NotImplemented'

    def validate(self, request, action):
        if action != action.lower():
            raise ValidationError(_('The action name must be in lower case.'))
        valid = self.valid_actions
        method = request.method
        if action in valid and method not in valid[action]:
            raise ValidationError(_("Method '%s' is forbidden for action.") % method)
        return True

    def routing(self, request, action=None, **kwargs):
        """Обеспечивает маршрутизацию к методам."""
        if action:
            self.validate(request, action)
        else:
            action = request.method.lower()
        handler = getattr(self, 'action_%s' % action, None)
        if not handler:
            raise NotExistError(_("Action '%s' not exist.") % action)
        return handler(request, **kwargs)

    # Получить
    def action_get(self, request, **kwargs):
        raise NotImplementedError()

    # Создать
    def action_create(self, request, **kwargs):
        user = request.user
        if not user.has_perm(self.add_perm):
            raise PermissionDenied()

        model_form = self.get_model_form(request)

        form = model_form(request.data, files=request.FILES)
        if form.is_valid():
            o = form.save()
        else:
            # TODO: сделать лог
            raise ValidationError(form.errors)
        return self.render_objects(request, [o])[0]

    def action_post(self, *args, **kwargs):
        return self.action_create(*args, **kwargs)

    # Обновить
    def action_update(self, request, **kwargs):
        user = request.user
        if not user.has_perm(self.change_perm):
            raise PermissionDenied()

        list_id = self.get_list_id(request, **kwargs)
        files = request.FILES
        data = request.data
        fields = files.keys()
        fields.extend([x for x in data.keys() if x != 'id'])
        model_form = self.get_model_form(request, fields)

        qs = self.get_queryset(request, **kwargs)
        qs = qs.filter(pk__in=list_id)
        result = []
        try:
            for o in qs:
                form = model_form(data, files=files, instance=o)
                if form.is_valid():
                    form.save()
                    result.append(o)
                else:
                    raise ValidationError()
                # TODO: сделать лог
        except Exception as e:
            pass # TODO: сделать лог
        # Если задан был один объект на обновление, то один и вернём.
        data = self.render_objects(request, result)
        if len(list_id) == 1:
            return data[0] if data else None
        return data

    def action_put(self, *args, **kwargs):
        return self.action_update(*args, **kwargs)

    def action_patch(self, *args, **kwargs):
        return self.action_update(*args, **kwargs)

    # Удалить
    def action_delete(self, request, **kwargs):
        user = request.user
        if not user.has_perm(self.delete_perm):
            raise PermissionDenied()

        list_id = self.get_list_id(request, **kwargs)
        qs = self.get_queryset(request, **kwargs)
        qs = qs.filter(pk__in=list_id)
        result = []
        try:
            for o in qs:
                pk = o.pk
                o.delete()
                result.append(pk)
        except Exception as e:
            pass # TODO: сделать лог
        return result

    # Начальные данные
    def action_defaults(self, request, **kwargs):
        """
        Возвращает дефолтные значения для полей, в которых таковые определены.

        """
        return {f.name: f.get_default() for f in self.default_fields}

    # Схема
    def action_scheme(self, request, **kwargs):
        """Возвращает схему контроллера."""
        return self.get_scheme(request, **kwargs)

    # Поиск по внешней модели.
    def action_fkey(self, request, **kwargs):
        """Возвращает данные для модели внешнего соединения."""
        REQUEST = {k: request.GET[k] for k in request.GET.keys()}
        query = REQUEST.get(self.search_key, None)
        fname = REQUEST.get(self.foreign_key, None)
        # Маппинг по колонкам выполняется только для модели.
        if hasattr(self, 'map_column_field'):
            if fname in self.map_column_field:
                fname = self.map_column_field[fname]
        try:
            assert fname is not None
            names = fname.split('__')
            model = self.model
            for name in names:
                field = model._meta.get_field(name)
                model = field.rel.model
        except:
            raise ValidationError(_('Please send correct relation name.'))
        ctrl = get_controller(field.rel.model)
        return ctrl.model_ctrl.simple_search(request, query, **kwargs)


class ModelController(BaseController):
    """Контроллер операций с коллекцией объектов (моделью)."""
    # Список фильтров автоматически заполняется всеми собственными полями
    # и полями всех отношений, если не указан пустой список
    filters = None
    # Список колонок состоит из словарей, сформированных с помощью функции
    # serialize_field()
    columns = None
    order_columns = None # список имён колонок, по которым можно делать
                         # сортировку
    search_fields = None # список полей для общего поиска (см.`search_key`)
    map_column_field = None # связывание колонок с реальными полями
    map_column_relation = None # связывание колонок с другими моделями на клиенте
    columns_key  = 'c' # ключ, по которому принимается список полей для рендеринга
    ordering_key = 'o' # ключ, по которому с клиента принимается сортировка
    limit_key    = 'l' # ключ, по которому с клиента принимается лимит записей
    page_key     = 'p' # ключ, по которому с клиента принимается № страницы
    limit     = 10 # рабочий лимит возвращаемых записей
    max_limit = 50 # максимальный лимит возвращаемых записей, который
                   # не позволяет убить сервер огромными наборами данных

    def __init__(self, *args, **kwargs):
        """Инициализация."""
        super(ModelController, self).__init__(*args, **kwargs)

        self.default_ordering = self.model._meta.ordering

        if self.map_column_field is None:
            self.map_column_field = {}
        if self.map_column_relation is None:
            self.map_column_relation = {}

        self.autoset_filters()
        self.autoset_columns()

        if self.order_columns is None:
            self.order_columns = [f.name for f in self.visible_fields \
                                               if not f.related_model]
        if self.search_fields is None:
            fields = [f.name for f in self.visible_fields if
                            isinstance(f, CharField) and f.name != 'password']
            if not fields:
                for field in self.visible_fields:
                    rel = field.related_model
                    if rel:
                        prefix = field.name + '__%s'
                        fields.extend([
                            prefix % f.name for f in rel._meta.fields if
                            not f.hidden and isinstance(f, CharField) and
                            f.name != 'password'
                        ])
            self.search_fields = fields

    def autoset_filters(self):
        def serialize(f, parent=None):
            data = {'type': f.__class__.__name__}
            if parent:
                data['name'] = '%s__%s' % (parent.name, f.name)
                data['display_name'] = join_display_names_lazy(
                    parent.verbose_name, f.verbose_name
                )
            else:
                data['name'] = f.name
                data['display_name'] = f.verbose_name
            if f.choices:
                data['choices'] = f.get_choices(include_blank=False)
            return data

        if self.filters is None:
            L = []
            for field in self.all_fields:
                if field.name == 'password':
                    continue
                L.append(serialize(field))
                rel = field.related_model
                if rel:
                    L.extend([
                        serialize(f, field) for f in rel._meta.fields if
                                                f.name != 'password'
                    ])
            self.filters = L

    def autoset_columns(self):
        def test(f):
            return bool(hasattr(f, 'auto_now_add') or
                        hasattr(f, 'auto_now') or not
                        (f.hidden or f.name == 'password'))

        if self.columns is None:
            self.columns = [serialize_field(f) for f in self.all_fields if test(f)]

    def get_scheme(self, request, **kwargs):
        """
        Возвращает схему модели, с помощью которой на клиенте можно отображать
        объекты модели.

        """
        data = {
            'filters': self.filters,
            'columns': self.columns,
            'default_ordering': self.default_ordering,
            'order_columns': self.order_columns,
            'map_column_relation': self.map_column_relation,
            'columns_key': self.columns_key,
            'ordering_key': self.ordering_key,
            'search_key': self.search_key if self.search_fields else None,
            'limit_key': self.limit_key,
            'page_key': self.page_key,
            'foreign_key': self.foreign_key,
            'limit': self.limit,
            'max_limit': self.max_limit,
        }
        return data

    def render_column(self, request, obj, column):
        """Рендерит колонку для записи из базы данных."""
        if column in ('__unicode__', '__str__'):
            return force_text(obj)
        column = column.replace('__', '.')
        display = 'get_%s_display' % column
        if hasattr(obj, display):
            # It's a choice field
            return getattr(obj, display)()
        else:
            return self.render_field(request, obj, column)

    def render_objects(self, request, qs, columns=None):
        """Рендерит весь полученный QuerySet."""
        render = self.render_column
        M = self.map_column_field
        fields = [M.get(col['name'], col['name']) for col in self.columns if
                  columns is None or col['name'] in columns]
        meta = self.model._meta
        app_label  = meta.app_label
        model_name = meta.model_name
        def serialize(o):
            reverse_args = (app_label, model_name, o.pk)
            return {
                'fields': {f: render(request, o, f) for f in fields},
                'pk': o.pk,
                'display_name': force_text(o),
                'url': reverse('directapps:object', args=reverse_args)
            }
        return map(serialize, qs)

    def filtering(self, request, qs, filters):
        """Производит фильтрацию набора данных."""
        if not filters:
            return qs

        map_keys = self.map_column_field.keys()
        field_names = self.all_fields_names
        exists = lambda f: f in map_keys or f in field_names

        def parse_filter(f):
            inverse = False
            if f.startswith('-'):
                inverse = True
                f = f[1:]
            op = 'exact'
            if '__' in f:
                l = f.split('__')
                if not exists(l[0]):
                    # нет такого поля
                    return None, None
                if l[-1] in LOOKUPS_KEYS:
                    f = '__'.join(l[:-1])
                    op = l[-1]
            elif not exists(f):
                return None, None, None
            return self.map_column_field.get(f, f), op, inverse

        for f, query in filters.items():
            if f == self.search_key:
                qs = smart_search(qs, self.search_fields, query)
                continue
            field, op, inverse = parse_filter(f)
            if field:
                if op == 'isnull':
                    query = bool(query == 'true')
                elif op in ('in', 'range'):
                    query = query.split(',')
                if inverse:
                    func = qs.exclude
                else:
                    func = qs.filter
                qs = func(Q(**{'%s__%s' % (field, op): query}))
        return qs

    def ordering(self, request, qs, ordering):
        """
        Функция проверяет параметры сортировки и применяет только валидную.
        """
        if not ordering:
            return qs
        def valid(x):
            return bool(x and not x.startswith('--') and x.lstrip('-') in self.order_columns)
        o = [x for x in ordering.split(',') if valid(x)]
        if o:
            qs = qs.order_by(*o)
        return qs

    def paging(self, request, qs, page, limit, orphans=0):
        """Функция возвращает объект Page паджинатора."""
        return Paginator(qs, per_page=limit, orphans=orphans).page(page)

    def info(self, request, qs):
        """Возвращает информацию о наборе. Для переопределения."""
        return None

    def context(self, request, page, info, columns):
        """Формирование контекста JSON структуры."""
        data =  {
            'objects': self.render_objects(request, page.object_list, columns),
            'page': page.number,
            'num_pages': page.paginator.num_pages,
            'info': info,
        }
        return data

    def action_get(self, request, **kwargs):
        """Стандартное получение данных."""
        REQUEST = {k: request.GET[k] for k in request.GET.keys()}
        page  = REQUEST.pop(self.page_key, None)
        page  = int(page or 1)
        limit = REQUEST.pop(self.limit_key, None)
        limit = int(limit or self.limit)
        if limit > self.max_limit:
            limit = self.max_limit
        ordering = REQUEST.pop(self.ordering_key, None)
        columns = REQUEST.pop(self.columns_key, None)
        if columns is not None:
            columns = columns.split(',')
        filters  = REQUEST
        # Получаем весь QuerySet вместе с зависимыми объектами
        qs = self.get_queryset(request, **kwargs) # **kwargs нужен наследникам!
        if isinstance(self.select_related, (list, tuple)):
            qs = qs.select_related(*self.select_related)
        elif self.select_related:
            qs = qs.select_related()
        if isinstance(self.prefetch_related, (list, tuple)):
            qs = qs.prefetch_related(*self.prefetch_related)
        elif self.prefetch_related:
            qs = qs.prefetch_related()
        # Отфильтровываем, отсортировываем и рендерим результат.
        qs   = self.filtering(request, qs, filters)
        info = self.info(request, qs)
        qs   = self.ordering(request, qs, ordering)
        page = self.paging(request, qs, page, limit)
        ctx  = self.context(request, page, info, columns)
        return ctx

    def simple_search(self, request, query, **kwargs):
        """Простой поиск объектов модели."""
        qs = self.get_queryset(request)
        if query:
            if not self.search_fields:
                qs = qs.filter(pk=query)
            else:
                qs = self.filtering(request, qs, {self.search_key: query})
        def serialize(o):
            return {
                'pk': o.pk,
                'display_name': force_text(o),
            }
        return map(serialize, qs[:10])


class RelationController(ModelController):
    """Контроллер операций со связанными моделями."""

    def __init__(self, rel):
        """Инициализация."""
        self.rel = rel
        self.field_name = rel.field.name
        super(RelationController, self).__init__(rel.related_model)
        self.relation_name = force_text(self.model._meta)

    def autoset_columns(self):
        if self.columns is None:
            self.columns = [serialize_field(f) for f in self.visible_fields if
                            f.name != self.field_name]

    def get_queryset(self, request, object, **kwargs):
        qs = super(RelationController, self).get_queryset(request)
        qs = qs.filter(**{'%s__exact' % self.field_name: object})
        return qs

    def get_scheme(self, request, **kwargs):
        data = super(RelationController, self).get_scheme(request, **kwargs)
        data['relation'] = self.relation_name
        return data


class ObjectController(BaseController):
    """Контроллер операций с объектом."""

    # Эти 2 параметра определяются совместно
    relations = None # список связанных моделей с их названиями [('order', 'Заказы'),]
    map_relation_ctrl = None # карта связанных моделей и их контроллеров

    def __init__(self, *args, **kwargs):
        """Инициализация."""
        super(ObjectController, self).__init__(*args, **kwargs)

        meta = self.model._meta
        self.serialized_fields = [serialize_field(f) for f in self.visible_fields]

        if self.map_relation_ctrl is None:
            self.map_relation_ctrl = {}

        if self.relations is None:
            R = []
            for rel in meta.related_objects:
                ctrl = RelationController(rel)
                self.map_relation_ctrl[rel.name] = ctrl
                R.append([rel.name, rel.related_model._meta.verbose_name_plural])
            self.relations = R

    def get_scheme(self, request, **kwargs):
        """
        Возвращает схему модели, с помощью которой на клиенте можно создавать
        или обновлять объекты модели.

        """
        data = {
            'fields': self.serialized_fields,
            'relations': [
                {
                    'name': r[0],
                    'display_name': r[1],
                    'relation': self.map_relation_ctrl[r[0]].relation_name
                } for r in self.relations
            ],
            'foreign_key': self.foreign_key,
            'search_key': self.search_key,
        }
        return data

    def routing(self, request, relation=None, **kwargs):
        """Обеспечивает маршрутизацию к методам (отношений или собственным)."""
        if relation:
            try:
                ctrl = self.map_relation_ctrl[relation]
            except KeyError:
                raise NotExistError(_("Relation '%s' not exist.") % relation)
            return ctrl.routing(request, **kwargs)
        return super(ObjectController, self).routing(request, **kwargs)

    def action_get(self, request, object, **kwargs):
        """Возвращает объект модели."""
        qs = self.get_queryset(request)
        obj = qs.get(pk=object)
        return self.render_objects(request, [obj])[0]


class MasterController(object):
    """
    Мастер-контроллер, объединяющий в себе другие контроллеры и выполняющий
    роутинг к ним.

    """
    model_ctrl = None
    model_ctrl_class = ModelController
    object_ctrl = None
    object_ctrl_class = ObjectController

    def contribute_to_class(self, model, name):
        """
        Метод вызывается при добавлении мастер-контроллера в модель через
        model.add_to_class(), либо в момент инициализации модели, у которой
        контроллер определён атрибутом.

        """
        # Используем weakref из-за возможной утечки памяти (циклическая ссылка).
        self.model = weakref.ref(model)()
        self.name = name
        setattr(model, name, self)
        # Создаём ссылку, по которой будет доступен мастер-контроллер
        if not getattr(model, ATTRIBUTE_NAME, None):
            setattr(model, ATTRIBUTE_NAME, weakref.ref(self)())
        # Устанавливаем все необходимые суб-контроллеры.
        self.install_ctrls()

    def install_ctrls(self):
        """Устанавливает экземпляры всех необходимых контроллеров."""
        self.model_ctrl  = self.model_ctrl_class(self.model)
        self.object_ctrl = self.object_ctrl_class(self.model)

    def routing(self, request, **kwargs):
        """Обеспечивает маршрутизацию к суб-контроллерам."""
        if 'object' in kwargs:
            return self.object_ctrl.routing(request, **kwargs)
        return self.model_ctrl.routing(request, **kwargs)

    def get_scheme(self, request, **kwargs):
        """Возвращает полную схему модели."""
        scheme = self.model_ctrl.get_scheme(request)
        scheme['object'] = self.object_ctrl.get_scheme(request)
        return scheme


def get_controller(model):
    """Возвращает экземпляр связанного с моделью контроллера."""
    name = ATTRIBUTE_NAME
    if not hasattr(model, name):
        # set controller to model
        m = model._meta
        ctrl = CONTROLLERS.get('%s.%s' % (m.app_label, m.model_name))
        if ctrl:
            ctrl = import_string(ctrl)()
        elif MASTER_CONTROLLER:
            ctrl = import_string(MASTER_CONTROLLER)()
        else:
            ctrl = MasterController()
        model.add_to_class(name, ctrl)
    elif not isinstance(getattr(model, name), MasterController):
        ctrl = getattr(model, name)()
        model.add_to_class(name, ctrl)
    return getattr(model, name)

