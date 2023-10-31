import asyncio
from functools import reduce
from typing import (
    Any,
    cast,
    ClassVar,
    ForwardRef,
    List,
    Optional,
    Tuple,
    Type,
    TYPE_CHECKING,
    Union,
)
from typing_extensions import dataclass_transform, Self

from cherry.database import Database
from cherry.exception import *
from cherry.fields.fields import (
    BaseField,
    Field,
    ForeignKeyField,
    ManyToManyField,
    Relationship,
    RelationshipField,
    ReverseRelationshipField,
)
from cherry.fields.proxy import JsonFieldProxy, RelatedModelProxy
from cherry.fields.types import get_sqlalchemy_type_from_field
from cherry.fields.utils import (
    classproperty,
)
from cherry.meta.meta import init_meta_config, MetaConfig, mix_meta_config
from cherry.meta.pydantic_config import generate_pydantic_config
from cherry.queryset.queryset import QuerySet
from cherry.typing import AnyMapping, DictStrAny

from pydantic import PrivateAttr
from pydantic.fields import FieldInfo
from pydantic.main import BaseModel, ModelMetaclass
from sqlalchemy import Column, ForeignKey, Index, MetaData, Table
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.operators import and_


@dataclass_transform(kw_only_default=True, field_specifiers=(Field, Relationship))
class ModelMeta(ModelMetaclass):
    def __new__(
        cls: type["ModelMeta"],
        name: str,
        bases: Tuple[Type[Any], ...],
        attrs: DictStrAny,
        **kwargs: Any,
    ) -> "ModelMeta":
        generate_pydantic_config(attrs)

        meta = type("Meta", (MetaConfig,), {})
        for base in reversed(bases):
            if base != BaseModel and issubclass(base, Model):
                meta = mix_meta_config(base.__meta__, MetaConfig)
        init_meta_config(meta)
        meta.tablename = name
        if meta.abstract:
            meta.abstract = False

        allowed_meta_kwargs = {
            key
            for key in dir(meta)
            if not (key.startswith("__") and key.endswith("__"))
        }
        meta_kwargs = {
            key: kwargs.pop(key) for key in kwargs.keys() & allowed_meta_kwargs
        }
        attrs["__meta__"] = mix_meta_config(attrs.get("Meta"), meta, **meta_kwargs)

        new_cls = cast(Type["Model"], super().__new__(cls, name, bases, attrs))

        meta_config = new_cls.__meta__

        for model_field in new_cls.__fields__.values():
            if model_field.field_info.__class__ is FieldInfo:
                model_field.field_info = BaseField.from_base_field_info(
                    model_field.field_info,
                )
            field_info = model_field.field_info
            if isinstance(field_info, BaseField):
                if field_info.nullable is None:
                    field_info.nullable = model_field.allow_none
            elif isinstance(
                field_info,
                RelationshipField,
            ):
                if field_info.nullable is None:
                    field_info.nullable = model_field.allow_none
                field_info.related_model = model_field.type_  # type: ignore
            else:
                raise FieldTypeError(
                    (
                        'Field type must be "cherry.Field", got unexpected type: '
                        f' {field_info.__class__}'
                    ),
                )

        if not meta_config.abstract and hasattr(meta_config, "database"):
            meta_config.database.add_model(new_cls)
            meta_config.primary_key = tuple(
                field.name
                for field in new_cls.__fields__.values()
                if isinstance(field.field_info, BaseField)
                and field.field_info.primary_key
            )
            if len(meta_config.primary_key) == 0:
                raise PrimaryKeyMissingError(
                    f"Model {new_cls} must have at least one primary key",
                )

        return new_cls


class Model(BaseModel, metaclass=ModelMeta):
    if TYPE_CHECKING:
        __meta__: ClassVar[Type[MetaConfig]]

    if TYPE_CHECKING:
        __cherry_foreign_key_values__: DictStrAny
    else:
        __cherry_foreign_key_values__: DictStrAny = PrivateAttr(default_factory=dict)

    @classproperty
    def tablename(cls) -> str:
        """models's tablename in database"""
        return cls.__meta__.tablename

    @classproperty
    def database(cls) -> Database:
        """models's database object"""
        if cls.__meta__.abstract:
            raise AbstractModelError(
                f"Cannot get database from abstract model {cls}",
            )
        if not hasattr(cls.__meta__, "database"):
            raise DatabaseNoBoundError(
                f"Model {cls} has no been bound to any database",
            )
        return cls.__meta__.database

    @classproperty
    def table(cls) -> Table:
        """models's sqlalchemy table object"""
        if not hasattr(cls.__meta__, "table"):
            return cls._generate_sqlalchemy_table(cls.database._metadata)
        return cls.__meta__.table

    async def insert(self, exclude_related: bool = False) -> Self:
        """insert model into database and update primary key"""
        async with self.database as conn:
            result = await conn.execute(
                self.table.insert().values(
                    **self._extract_db_fields(exclude_related=exclude_related),
                ),
            )
            if result.inserted_primary_key:
                self.update_from_dict(result.inserted_primary_key._asdict())
            if not exclude_related:
                for name, rfield in self.__meta__.reverse_related_fields.items():
                    if related_values := getattr(self, name, None):
                        related_values = cast(List[Model], related_values)
                        await asyncio.gather(
                            *[
                                value.update(**{rfield.related_field_name: self})
                                for value in related_values
                            ],
                        )
        return self

    async def insert_with_related(self, *args: Any) -> Self:
        await self.insert(exclude_related=True)
        table_names = self._get_related_tables(*args)
        async with self.database as conn:
            for name, rfield in self.__meta__.related_fields.items():
                if (
                    table_names is not None
                    and rfield.related_model.tablename not in table_names
                ):
                    continue
                if (related_value := getattr(self, name, None)) and isinstance(
                    related_value,
                    Model,
                ):
                    await related_value.insert()
                    # this results in recursive references to the model
                    # if rfield.related_field_name is not None:
                    #     value_related_field = getattr(
                    #         related_value,
                    #         rfield.related_field_name,
                    #         None,
                    #     )
                    #     if isinstance(value_related_field, list):
                    #         value_related_field.append(self)
                    #     else:
                    #         setattr(related_value, rfield.related_field_name, [self])

                else:
                    raise FieldTypeError(
                        f"Related field {self.__class__}.{name} must be a Model",
                    )

            for name, rfield in self.__meta__.reverse_related_fields.items():
                if (
                    table_names is not None
                    and rfield.related_model.tablename not in table_names
                ):
                    continue
                if related_value := getattr(self, name, None):
                    if rfield.is_list:
                        if isinstance(related_value, list) and all(
                            isinstance(v, Model) for v in related_value
                        ):
                            await rfield.related_model.insert_many(*related_value)
                        else:
                            raise FieldTypeError(
                                (
                                    f"Related field {self.__class__}.{name} must be a"
                                    " list of Model"
                                ),
                            )
                    else:
                        if isinstance(related_value, Model):
                            await related_value.insert()
                        else:
                            raise FieldTypeError(
                                (
                                    f"Related field {self.__class__}.{name} must be a"
                                    " Model"
                                ),
                            )

            for name, rfield in self.__meta__.many_to_many_fields.items():
                if (
                    table_names is not None
                    and rfield.related_model.tablename not in table_names
                ):
                    continue
                if related_value := getattr(self, name, None):
                    if isinstance(related_value, list) and all(
                        isinstance(v, Model) for v in related_value
                    ):
                        insert_values = [
                            {
                                rfield.m2m_table_field_name: getattr(
                                    self,
                                    rfield.m2m_field_name,
                                ),
                                rfield.related_field.m2m_table_field_name: getattr(
                                    v,
                                    rfield.related_field.m2m_field_name,
                                ),
                            }
                            for v in related_value
                        ]
                        await conn.execute(
                            rfield.table.insert(),
                            insert_values,
                        )
                    else:
                        raise FieldTypeError(
                            (
                                f"Related field {self.__class__}.{name} must be a list"
                                " of Model"
                            ),
                        )

        return self

    async def update(self, **kwargs: Any) -> Self:
        """update model with given data"""
        async with self.database as conn:
            if self._check_pk_null():
                raise PrimaryKeyMissingError("Primary key can not be null when update")
            self.update_from_dict(kwargs)
            await conn.execute(
                self.table.update()
                .where(self.get_pk_filter())
                .values(**self._extract_db_fields(exclude_pk=True)),
            )
        return self

    async def fetch(self, related: bool = False) -> Self:
        """fetch data from database by primary key"""
        async with self.database as conn:
            if self._check_pk_null():
                raise PrimaryKeyMissingError("Primary key can not be null when fetch")
            result = await conn.execute(
                self.table.select().where(self.get_pk_filter()),
            )
            if result_one := result.fetchone():
                self.update_from_dict(result_one._asdict())
            if related:
                await self.fetch_related()
        return self

    async def fetch_related(self, *args: Any) -> Self:
        """fetch related data from database by related field"""
        self_dict = self._extract_db_fields(exclude_related=True)
        async with self.database as conn:
            table_names = self._get_related_tables(*args)
            for name, rfield in self.__meta__.related_fields.items():
                if (
                    table_names is not None
                    and rfield.related_model.tablename not in table_names
                ):
                    continue
                if (
                    rfield.foreign_key_self_name
                    not in self.__cherry_foreign_key_values__
                ):
                    raise RelatedFieldMissingError(
                        (
                            "Can not fetch related model if not been inserted into or"
                            " fetched from database"
                        ),
                    )
                related_data = await conn.execute(
                    rfield.related_model.table.select().where(
                        getattr(rfield.related_model, rfield.foreign_key)
                        == self.__cherry_foreign_key_values__[
                            rfield.foreign_key_self_name
                        ],
                    ),
                )
                if related_one := related_data.fetchone():
                    setattr(
                        self,
                        name,
                        rfield.related_model.parse_from_db_dict(related_one._asdict()),
                    )
                else:
                    if rfield.nullable:
                        setattr(self, name, None)
                    else:
                        raise NoMatchDataError(
                            f"No matching data for {self.__class__}.{name}",
                        )

            for name, rfield in self.__meta__.reverse_related_fields.items():
                if (
                    table_names is not None
                    and rfield.related_model.tablename not in table_names
                ):
                    continue
                foreign_key_value = getattr(
                    self,
                    rfield.related_field.foreign_key,
                    None,
                )
                if foreign_key_value is None:
                    raise RelatedFieldMissingError(
                        (
                            "Can not fetch related model if not been inserted into or"
                            " fetched from database"
                        ),
                    )
                related_data = await conn.execute(
                    rfield.related_model.table.select().where(
                        getattr(
                            rfield.related_model,
                            rfield.related_field.foreign_key_self_name,
                        )
                        == foreign_key_value,
                    ),
                )
                if rfield.is_list:
                    setattr(
                        self,
                        name,
                        [
                            rfield.related_model.parse_from_db_dict(
                                (
                                    {
                                        **related_one._asdict(),
                                        rfield.related_field_name: self_dict,
                                    }
                                ),
                            )
                            for related_one in related_data.fetchall()
                        ],
                    )
                else:
                    if related_one := related_data.fetchone():
                        setattr(
                            self,
                            name,
                            rfield.related_model.parse_from_db_dict(
                                (
                                    {
                                        **related_one._asdict(),
                                        rfield.related_field_name: self_dict,
                                    }
                                ),
                            ),
                        )
                    else:
                        if rfield.nullable:
                            setattr(self, name, None)
                        else:
                            raise NoMatchDataError(
                                f"No matching data for {self.__class__}.{name}",
                            )
            for name, field in self.__meta__.many_to_many_fields.items():
                if (
                    table_names is not None
                    and field.related_model.tablename not in table_names
                ):
                    continue
                m2m_field_value = getattr(self, field.m2m_field_name, None)
                if m2m_field_value is None:
                    raise RelatedFieldMissingError(
                        (
                            "Can not fetch related model if not been inserted into or"
                            " fetched from database"
                        ),
                    )
                related_data = await conn.execute(
                    field.related_model.table.select()
                    .select_from(field.related_model.table.join(field.table))
                    .join(self.table)
                    .where(self.table.c[field.m2m_field_name] == m2m_field_value),
                )
                setattr(
                    self,
                    name,
                    [
                        field.related_model.parse_from_db_dict(related_one._asdict())
                        for related_one in related_data.fetchall()
                    ],
                )
        return self

    async def save(self):
        """if model has been inserted into database, update it, else insert it"""
        async with self.database as conn:
            if self._check_pk_null():
                raise PrimaryKeyMissingError("Primary key can not be null when save")
            fetch = await conn.execute(
                self.table.select().where(self.get_pk_filter()),
            )
            if fetch:
                await self.update()
            else:
                await self.insert()

    async def delete(self) -> Self:
        """delete model from database"""
        if self._check_pk_null():
            raise PrimaryKeyMissingError("Primary key can not be null when delete")
        async with self.database as conn:
            await conn.execute(
                self.table.delete().where(self.get_pk_filter()),
            )
        return self

    @classmethod
    async def insert_many(cls, *models: Self):
        """insert many models into database"""
        if models:
            async with cls.database as conn:
                has_pk_model = [model for model in models if not model._check_pk_null()]
                no_pk_model = [model for model in models if model._check_pk_null()]
                if has_pk_model:
                    await conn.execute(
                        cls.table.insert(),
                        [model._extract_db_fields() for model in has_pk_model],
                    )
                for model in no_pk_model:
                    await model.insert()
                return None
        raise ModelMissingError("You must give at least one model to insert")

    @classmethod
    async def save_many(cls, *models: Self):
        """save many models into database"""
        if models:
            async with cls.database:
                await asyncio.gather(*[model.save() for model in models])
                return None
        raise ModelMissingError("You must give at least one model to save")

    @classmethod
    async def delete_many(cls, *models: Self) -> int:
        """delete many models from database"""
        if models:
            async with cls.database as conn:
                result = await conn.execute(
                    cls.table.delete(),
                    [model.dict(by_alias=True) for model in models],
                )
                return result.rowcount
        raise ModelMissingError("You must give at least one model to delete")

    @classmethod
    def select(cls) -> QuerySet[Self]:
        """query without any filter condition"""
        return QuerySet(cls)

    @classmethod
    def filter(cls, *args: Any, **kwargs: Any) -> QuerySet[Self]:
        """query with any filter condition"""
        return QuerySet(cls, *args, **kwargs)

    @classmethod
    def select_related(cls, *args: Any) -> QuerySet[Self]:
        """select and select related model at the same time"""
        return QuerySet(cls).prefetch_related(*args)

    @classmethod
    async def paginate(cls, page: int, page_size: int) -> List[Self]:
        """select with pagination"""
        return await QuerySet(cls).paginate(page, page_size)

    @classmethod
    async def first(cls) -> Optional[Self]:
        """select first model"""
        return await QuerySet(cls).first()

    @classmethod
    async def all(cls) -> List[Self]:
        """select all models"""
        return await QuerySet(cls).all()

    @classmethod
    async def random_one(cls) -> Optional[Self]:
        """select one model randomly"""
        return await QuerySet(cls).random_one()

    @classmethod
    async def get(cls, *args: Any, **kwargs: Any) -> Self:
        """select one model with filter condition, if not exist, raise error"""
        return await cls.filter(*args, **kwargs).get()

    @classmethod
    async def get_or_none(cls, *args: Any, **kwargs: Any) -> Optional[Self]:
        """select one model with filter condition, if not exist, return None"""
        try:
            return await cls.filter(*args, **kwargs).get()
        except NoMatchDataError:
            return None

    @classmethod
    async def get_or_create(
        cls,
        *args: Any,
        defaults: Optional[DictStrAny] = None,
        fetch_related: Union[bool, Tuple[Any, ...]] = False,
        **kwargs: Any,
    ) -> Tuple[Self, bool]:
        """select one model with filter condition, if not exist, create one"""
        queryset = cls.filter(*args, **kwargs)
        if fetch_related is True or isinstance(fetch_related, tuple):
            queryset = queryset.prefetch_related(
                () if fetch_related is True else fetch_related,
            )
        try:
            return await queryset.get(), True
        except NoMatchDataError:
            create_values = queryset._clause_list_to_dict()
            create_values.update(
                {
                    (k.name if isinstance(k, Column) else k): v
                    for k, v in (defaults or {}).items()
                },
            )
            return await cls(**create_values).insert(), False

    @classmethod
    async def update_or_create(
        cls,
        *args: Any,
        defaults: Optional[DictStrAny] = None,
        fetch_related: Union[bool, Tuple[Any, ...]] = False,
        **kwargs: Any,
    ) -> Tuple[Self, bool]:
        """update one model with filter condition,
        if not exist, create one with filter and defaults values"""
        queryset = cls.filter(*args, **kwargs)
        if fetch_related is True or isinstance(fetch_related, tuple):
            queryset = queryset.prefetch_related(
                () if fetch_related is True else fetch_related,
            )
        try:
            model = await queryset.get()
            return await model.update(**(defaults or {})), True
        except NoMatchDataError:
            create_values = queryset._clause_list_to_dict()
            create_values.update(
                {
                    (k.name if isinstance(k, Column) else k): v
                    for k, v in (defaults or {}).items()
                },
            )
            return await cls(**create_values).insert(), False

    async def add(self, model: "Model") -> Self:
        _, field = self._get_field_type_by_model(model)
        async with self.database as conn:
            if isinstance(field, ManyToManyField):
                await conn.execute(
                    field.table.insert().values(
                        {
                            field.m2m_table_field_name: getattr(
                                self,
                                field.m2m_field_name,
                            ),
                            field.related_field.m2m_table_field_name: getattr(
                                model,
                                field.related_field.m2m_field_name,
                            ),
                        },
                    ),
                )
                value = getattr(self, field.related_field.related_field_name)
                if isinstance(value, list):
                    value.append(model)
                else:
                    setattr(self, field.related_field.related_field_name, [model])
            elif isinstance(field, ReverseRelationshipField) and field.is_list:
                setattr(
                    model,
                    field.related_field_name,
                    self,
                )
                await model.save()
                value = getattr(self, field.related_field_name)
                if isinstance(value, list):
                    value.append(model)
                else:
                    setattr(self, field.related_field_name, [model])
            else:
                raise RelationSolveError(
                    f"There are no related fields associated with {type(model)} to add",
                )

        return self

    async def remove(self, model: "Model"):
        _, field = self._get_field_type_by_model(model)
        async with self.database as conn:
            if isinstance(field, ManyToManyField):
                await conn.execute(
                    field.table.delete().where(
                        field.table.c[field.m2m_table_field_name]
                        == getattr(self, field.m2m_field_name),
                    ),
                )
                getattr(self, field.related_field.related_field_name).remove(model)
            elif isinstance(field, ReverseRelationshipField) and field.is_list:
                await model.delete()
                getattr(self, field.related_field_name).remove(model)
            else:
                raise RelationSolveError(
                    (
                        f"There are no related fields associated with {type(model)} to"
                        " remove"
                    ),
                )

    def get_pk_filter(self) -> ColumnElement[bool]:
        """generate primary key filter condition"""
        return reduce(
            and_,
            (
                getattr(self.__class__, pk) == getattr(self, pk)
                for pk in self.__meta__.primary_key
            ),
        )

    @classmethod
    def get_pk_columns(cls) -> Tuple[Column, ...]:
        """get primary key columns"""
        return tuple(getattr(cls, pk) for pk in cls.__meta__.primary_key)

    @classmethod
    def parse_from_db_dict(cls, data: DictStrAny) -> Self:
        """parse model from database result dict"""
        model = cls.parse_obj(data)
        for foreign_key in cls.__meta__.foreign_keys:
            model.__cherry_foreign_key_values__[foreign_key] = data.pop(
                foreign_key,
                None,
            )
        return model

    def update_from_dict(self, update_data: AnyMapping):
        """update model from dict"""
        for k, v in update_data.items():
            if k in self.__fields__:
                setattr(self, k, v)
            elif k in self.__meta__.foreign_keys:
                self.__cherry_foreign_key_values__[k] = v

    def update_from_kwargs(self, **kwargs: Any):
        """update model from kwargs"""
        for k, v in kwargs.items():
            setattr(self, k, v)

    def _extract_db_fields(
        self,
        exclude_pk: bool = False,
        exclude_related: bool = False,
    ) -> DictStrAny:
        """extract database fields from model"""
        exclude = (
            self.__meta__.related_fields.keys()
            | self.__meta__.reverse_related_fields.keys()
            | self.__meta__.many_to_many_fields.keys()
        )
        if exclude_pk:
            exclude |= set(self.__meta__.primary_key)
        data = self.dict(by_alias=True, exclude=exclude)
        data = {k: list(v) if isinstance(v, set) else v for k, v in data.items()}
        if exclude_related:
            return data
        for field_name, field in self.__meta__.related_fields.items():
            self_value = getattr(self, field_name)
            if self_value is None:
                data[field.foreign_key_self_name] = None
                self.__cherry_foreign_key_values__[field.foreign_key_self_name] = None
                continue
            value = getattr(
                self_value,
                field.foreign_key,
            )
            data[field.foreign_key_self_name] = value
            self.__cherry_foreign_key_values__[field.foreign_key_self_name] = value
            if not field.nullable and not data[field.foreign_key_self_name]:
                raise ForeignKeyMissingError(
                    (
                        'Foreign key field'
                        f' "{self.__class__}.{field.foreign_key_self_name}" cannot be'
                        ' None when insert or update'
                    ),
                )
        return data

    def _check_pk_null(self) -> bool:
        """check if primary key is null"""
        return all(getattr(self, pk) is None for pk in self.__meta__.primary_key)

    @classmethod
    def update_forward_refs(cls, **localns: Any):
        """update forward refs and check model type"""
        super().update_forward_refs(**localns)
        model_type = []
        for _, field in cls.__fields__.items():
            field_info = field.field_info
            if isinstance(
                field_info,
                RelationshipField,
            ):
                if isinstance(field_info.related_model, ForwardRef):
                    field_info.related_model = field.type_
                if not issubclass(field_info.related_model, Model):
                    raise RelationSolveError(
                        (
                            'Related model must be a "cherry.Model", but got unexpected'
                            f' type {field_info.related_model}'
                        ),
                    )
                if field_info.related_model in model_type:
                    raise RelationSolveError(
                        (
                            f"Related model {field_info.related_model} can appear only"
                            f" once in {cls}"
                        ),
                    )
                model_type.append(field_info.related_model)

    @classmethod
    def _get_related_tables(cls, *args: Any) -> Optional[List[str]]:
        if args:
            table_names = []
            for arg in args:
                if isinstance(arg, Table):
                    table_names.append(arg.name)
                elif isinstance(arg, str):
                    table_names.append(arg)
                elif isinstance(arg, Column):
                    table_names.append(arg.table.name)
                elif isinstance(arg, RelatedModelProxy):
                    table_names.append(arg.related_model.tablename)
                elif issubclass(arg, Model):
                    table_names.append(arg.tablename)
                else:
                    raise FieldTypeError(
                        (
                            "Related args must be str, Column, Table or Model, not"
                            f" {type(arg)}"
                        ),
                    )
        else:
            table_names = None
        return table_names

    @classmethod
    def _get_field_type_by_model(cls, model: "Model") -> Tuple[str, RelationshipField]:
        for field_name, field in cls.__fields__.items():
            if isinstance(
                field.field_info,
                RelationshipField,
            ) and isinstance(model, field.field_info.related_model):
                return field_name, field.field_info
        raise FieldTypeError(
            f"There are no related fields associated with {cls}.{model}",
        )

    @classmethod
    def _generate_sqlalchemy_column(cls):
        if any(f for f in cls.__fields__.values() if isinstance(f.type_, ForwardRef)):
            cls.update_forward_refs()
        for model_field in cls.__fields__.values():
            field_info = model_field.field_info
            if isinstance(field_info, BaseField):
                type_, is_json = get_sqlalchemy_type_from_field(model_field)
                cls.__meta__.columns[model_field.name] = Column(
                    model_field.name,
                    type_=type_,
                    primary_key=field_info.primary_key,
                    nullable=field_info.nullable,
                    index=field_info.index,
                    unique=field_info.unique,
                    autoincrement=field_info.autoincrement,
                    default=field_info.default or field_info.default_factory or None,
                    **field_info.sa_column_extra,
                )
                if is_json:
                    setattr(
                        cls,
                        model_field.name,
                        JsonFieldProxy(cls.__meta__.columns[model_field.name]),
                    )
                else:
                    setattr(
                        cls,
                        model_field.name,
                        cls.__meta__.columns[model_field.name],
                    )
            elif isinstance(field_info, ForeignKeyField):
                if not hasattr(field_info, "related_field_name"):
                    for rname, rfield in field_info.related_model.__fields__.items():
                        has_flag = False
                        if (
                            isinstance(rfield.field_info, ReverseRelationshipField)
                            and rfield.field_info.related_model is cls
                            and (
                                rfield.field_info.related_field_name == model_field.name
                                or rfield.field_info.related_field_name is None
                            )
                        ):
                            has_flag = True
                            field_info.related_field_name = rname
                            field_info.related_field = rfield.field_info
                            rfield.field_info.related_field_name = model_field.name
                            rfield.field_info.related_field = field_info
                            break
                        if not has_flag:
                            field_info.related_field_name = None
                            field_info.related_field = None
                if (
                    not hasattr(field_info, "related_field")
                    and field_info.related_field_name is not None
                ):
                    field_info.related_field = cast(
                        ReverseRelationshipField,
                        field_info.related_model.__fields__[
                            field_info.related_field_name
                        ].field_info,
                    )
                if not hasattr(field_info, "foreign_key"):
                    if len(field_info.related_model.__meta__.primary_key) != 1:
                        raise PrimaryKeyMultipleError(
                            (
                                f'{cls} has multiple primary keys, you must'
                                ' explicitly give out foreign key through'
                                ' Relationship(foreign_key="some field")'
                            ),
                        )
                    field_info.foreign_key = (
                        field_info.related_model.__meta__.primary_key[0]
                    )
                field_info.foreign_key_self_name = f"{field_info.related_model.tablename}_{field_info.foreign_key}"  # noqa: E501
                cls.__meta__.columns[model_field.name] = Column(
                    f"{field_info.related_model.tablename}_{field_info.foreign_key}",
                    ForeignKey(
                        f"{field_info.related_model.tablename}.{field_info.foreign_key}",
                        onupdate=field_info.on_update
                        or (
                            field_info.related_field
                            and field_info.related_field.on_update
                        )
                        or "NO ACTION",
                        ondelete=field_info.on_delete
                        or (
                            field_info.related_field
                            and field_info.related_field.on_update
                        )
                        or "NO ACTION",
                        **field_info.foreign_key_extra,
                    ),
                    nullable=field_info.nullable,
                    **field_info.sa_column_extra,
                )
                cls.__meta__.related_fields[model_field.name] = field_info
                setattr(
                    cls,
                    model_field.name,
                    RelatedModelProxy(
                        cls,
                        field_info.related_model,
                        model_field.name,
                        field_info,
                    ),
                )
                setattr(
                    cls,
                    field_info.foreign_key_self_name,
                    cls.__meta__.columns[model_field.name],
                )
            elif isinstance(field_info, ReverseRelationshipField):
                # from pydantic.fields.py, 2 is list
                if model_field.shape == 2:
                    field_info.is_list = True
                elif model_field.shape != 1:
                    raise FieldTypeError(
                        (
                            'ReverseRelationshipField must be a "cherry.Model" type or'
                            ' alist of it'
                        ),
                    )
                if not hasattr(field_info, "related_field_name"):
                    for rname, rfield in field_info.related_model.__fields__.items():
                        if (
                            isinstance(rfield.field_info, ForeignKeyField)
                            and rfield.field_info.related_model is cls
                            and (
                                rfield.field_info.related_field_name == model_field.name
                                or rfield.field_info.related_field_name is None
                            )
                        ):
                            field_info.related_field_name = rname
                            field_info.related_field = rfield.field_info
                            rfield.field_info.related_field_name = model_field.name
                            rfield.field_info.related_field = field_info
                            break
                if hasattr(field_info, "related_field_name"):
                    cls.__meta__.reverse_related_fields[model_field.name] = field_info
                    setattr(
                        cls,
                        model_field.name,
                        RelatedModelProxy(
                            cls,
                            field_info.related_model,
                            model_field.name,
                            field_info,
                        ),
                    )
                    if not hasattr(field_info, "related_field"):
                        field_info.related_field = cast(
                            ForeignKeyField,
                            field_info.related_model.__fields__[
                                field_info.related_field_name
                            ].field_info,
                        )
                else:
                    raise RelationSolveError(
                        (
                            "There are no related fields associated with"
                            f" {cls}.{model_field.name}"
                        ),
                    )
            elif isinstance(field_info, ManyToManyField):
                if model_field.shape != 2:
                    raise FieldTypeError(
                        'ManyToManyField must be a list of "cherry.Model" type',
                    )
                if not hasattr(field_info, "m2m_field_name"):
                    if len(cls.__meta__.primary_key) != 1:
                        raise PrimaryKeyMultipleError(
                            (
                                f'{cls} has multiple primary keys, you must'
                                ' explicitly give out foreign key through'
                                ' Relationship(many_to_many="some field")'
                            ),
                        )
                    field_info.m2m_field_name = cls.__meta__.primary_key[0]
                if not hasattr(field_info, "related_field_name"):
                    for rname, rfield in field_info.related_model.__fields__.items():
                        if (
                            isinstance(rfield.field_info, ManyToManyField)
                            and rfield.field_info.related_model is cls
                            and (
                                (
                                    rfn := getattr(
                                        rfield.field_info,
                                        "related_field_name",
                                        None,
                                    )
                                )
                                is None
                                or rfn == model_field.name
                            )
                        ):
                            field_info.related_field_name = rname
                            field_info.related_field = rfield.field_info
                            rfield.field_info.related_field_name = model_field.name
                            rfield.field_info.related_field = field_info
                            break
                if not hasattr(field_info, "related_field_name"):
                    raise RelationSolveError(
                        (
                            "There are no related fields associated with"
                            f" {cls}.{model_field.name}"
                        ),
                    )
                if not hasattr(field_info, "related_field"):
                    field_info.related_field = cast(
                        ManyToManyField,
                        field_info.related_model.__fields__[
                            field_info.related_field_name
                        ].field_info,
                    )
                cls.__meta__.many_to_many_fields[model_field.name] = field_info
                setattr(
                    cls,
                    model_field.name,
                    RelatedModelProxy(
                        cls,
                        field_info.related_model,
                        model_field.name,
                        field_info,
                    ),
                )
        cls.__meta__.foreign_keys = tuple(
            f.foreign_key_self_name for f in cls.__meta__.related_fields.values()
        )
        return cls.__meta__.columns

    @classmethod
    def _generate_sqlalchemy_table(cls, metadata: MetaData) -> Table:
        if cls.__meta__.abstract:
            raise AbstractModelError("Can not generate table for abstract model")
        if hasattr(cls.__meta__, "table"):
            return cls.table
        cls.__meta__.metadata = metadata
        cls.__meta__.table = Table(
            cls.tablename,
            metadata,
            *cls.__meta__.columns.values(),
            *cls.__meta__.constraints,
        )
        # many to many table
        for field_name, field in cls.__meta__.many_to_many_fields.items():
            if (
                field.related_field_name
                in field.related_model.__meta__.many_to_many_fields
                and field_name not in cls.__meta__.many_to_many_tables
            ):
                field.m2m_table_field_name = f"{cls.tablename}_{field.m2m_field_name}"
                field.related_field.m2m_table_field_name = (
                    f"{field.related_model.tablename}"
                    f"_{field.related_field.m2m_field_name}"
                )
                tablenames = [cls.tablename, field.related_model.tablename]
                tablenames.sort()
                table = Table(
                    "_".join(tablenames),
                    metadata,
                    Column(
                        field.m2m_table_field_name,
                        cls.__meta__.columns[field.m2m_field_name].type,
                        ForeignKey(
                            f"{cls.tablename}.{field.m2m_field_name}",
                            onupdate=field.on_update
                            or (field.related_field and field.related_field.on_update)
                            or "NO ACTION",
                            ondelete=field.on_delete
                            or (field.related_field and field.related_field.on_update)
                            or "NO ACTION",
                        ),
                    ),
                    Column(
                        field.related_field.m2m_table_field_name,
                        field.related_model.__meta__.columns[
                            field.related_field.m2m_field_name
                        ].type,
                        ForeignKey(
                            f"{field.related_model.tablename}.{field.related_field.m2m_field_name}",
                            onupdate=field.on_update
                            or (field.related_field and field.related_field.on_update)
                            or "NO ACTION",
                            ondelete=field.on_delete
                            or (field.related_field and field.related_field.on_update)
                            or "NO ACTION",
                        ),
                    ),
                )
                field.table = table
                field.related_field.table = table
                cls.__meta__.many_to_many_tables[field_name] = table
                field.related_model.__meta__.many_to_many_tables[
                    field.related_field_name
                ] = table

        for index in cls.__meta__.indexes:
            columns: List[Column] = [
                (
                    f.get_column()
                    if isinstance((f := getattr(cls, column_name)), RelatedModelProxy)
                    else f
                )
                for column_name in index.columns
            ]
            Index(
                index.name,
                *columns,
                unique=index.unique,
                quote=index.quote,
                info=index.info,
            )
        return cls.table
