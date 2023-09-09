from typing import (
    Any,
    cast,
    ClassVar,
    Dict,
    ForwardRef,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    TYPE_CHECKING,
)
from typing_extensions import dataclass_transform, Self

from cherry.database import Database
from cherry.exception import *
from cherry.fields.fields import (
    BaseField,
    ForeignKeyField,
    ManyToManyField,
    ReverseRelationshipField,
)
from cherry.fields.types import get_sqlalchemy_type_from_field
from cherry.fields.utils import classproperty
from cherry.meta.meta import init_meta_config, MetaConfig, mix_meta_config
from cherry.meta.pydantic_config import generate_pydantic_config
from cherry.queryset.queryset import QuerySet

from pydantic import PrivateAttr
from pydantic.fields import Field, FieldInfo
from pydantic.main import BaseModel, ModelMetaclass
from sqlalchemy import Column, ForeignKey, MetaData, Table
from sqlalchemy.sql.elements import ColumnElement


@dataclass_transform(kw_only_default=True, field_specifiers=(Field, FieldInfo))
class ModelMeta(ModelMetaclass):
    def __new__(
        cls: type["ModelMeta"],
        name: str,
        bases: Tuple[Type[Any], ...],
        attrs: Dict[str, Any],
        **kwargs: Any,
    ) -> "ModelMeta":
        generate_pydantic_config(attrs)

        meta = type("Meta", (MetaConfig,), {})
        for base in reversed(bases):
            if base != BaseModel and issubclass(base, Model):
                meta = mix_meta_config(base.__meta__, MetaConfig)
        init_meta_config(meta)
        meta.tablename = name

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
                field_info.nullable = model_field.allow_none
            elif isinstance(field_info, (ReverseRelationshipField, ForeignKeyField)):
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

        return new_cls


class Model(BaseModel, metaclass=ModelMeta):
    if TYPE_CHECKING:
        __meta__: ClassVar[Type[MetaConfig]]

    __foreign_key_values__: Dict[str, Any] = PrivateAttr(default_factory=dict)

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

    async def insert(self) -> Self:
        """insert model into database and update primary key"""
        result = await self.database.execute(
            self.table.insert().values(
                **self._extract_db_fields(),
            ),
        )
        if result.inserted_primary_key:
            self.update_from_dict(result.inserted_primary_key._asdict())
        return self

    async def update(self, **kwargs: Any) -> Self:
        """update model with given data"""
        if self._check_pk_null():
            raise PrimaryKeyMissingError("Primary key can not be null when update")
        self.update_from_dict(kwargs)
        await self.database.execute(
            self.table.update()
            .values(**self._extract_db_fields(exclude_pk=True))
            .where(*self.pk_filter),
        )
        return self

    async def fetch(self) -> Self:
        """fetch data from database by primary key"""
        if self._check_pk_null():
            raise PrimaryKeyMissingError("Primary key can not be null when fetch")
        result = await self.database.execute(
            self.table.select().where(*self.pk_filter),
        )
        if result_one := result.fetchone():
            self.update_from_dict(result_one._asdict())
        return self

    async def fetch_related(self, *tables: Any) -> Self:
        """fetch related data from database by related field"""
        table_names = self._get_related_tables(*tables)
        for name, rfield in self.__meta__.related_fields.items():
            if (
                table_names is not None
                and rfield.related_model.tablename not in table_names
            ):
                continue
            if rfield.foreign_key_self_name not in self.__foreign_key_values__:
                raise RelatedFieldMissingError(
                    (
                        "Can not fetch related model if not been inserted into or"
                        " fetched from database"
                    ),
                )
            related_data = await self.database.execute(
                rfield.related_model.table.select().where(
                    getattr(rfield.related_model, rfield.foreign_key)
                    == self.__foreign_key_values__[rfield.foreign_key_self_name],
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
            foreign_key_value = getattr(self, rfield.related_field.foreign_key, None)
            if foreign_key_value is None:
                raise RelatedFieldMissingError(
                    (
                        "Can not fetch related model if not been inserted into or"
                        " fetched from database"
                    ),
                )
            related_data = await self.database.execute(
                rfield.related_model.table.select().where(
                    getattr(
                        rfield.related_model,
                        rfield.related_field_name,
                    )
                    == foreign_key_value,
                ),
            )
            if rfield.is_list:
                setattr(
                    self,
                    name,
                    [
                        rfield.related_model.parse_from_db_dict(related_one._asdict())
                        for related_one in related_data.fetchall()
                    ],
                )
            else:
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
        for name, field in self.__meta__.many_to_many_fields.items():
            if (
                table_names is not None
                and field.related_model.tablename not in table_names
            ):
                continue
            m2m_field_value = getattr(self, field.m2m_field, None)
            if m2m_field_value is None:
                raise RelatedFieldMissingError(
                    (
                        "Can not fetch related model if not been inserted into or"
                        " fetched from database"
                    ),
                )
            related_data = await self.database.execute(
                field.table.select().where(
                    getattr(
                        field.table.c,
                        f"{self.tablename}_{field.m2m_field}",
                    )
                    == m2m_field_value,
                ),
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

    async def save(self) -> Self:
        """if model has been inserted into database, update it, else insert it"""
        if self._check_pk_null():
            raise PrimaryKeyMissingError("Primary key can not be null when save")
        fetch = await self.database.execute(
            self.table.select().where(*self.pk_filter),
        )
        if fetch:
            await self.update()
        else:
            return await self.insert()
        return self

    async def delete(self) -> Self:
        """delete model from database"""
        if self._check_pk_null():
            raise PrimaryKeyMissingError("Primary key can not be null when delete")
        await self.database.execute(
            self.table.delete().where(*self.pk_filter),
        )
        return self

    @classmethod
    async def insert_many(cls, *models: Self, need_pk_update: bool = False):
        """insert many models into database"""
        if models:
            if need_pk_update:
                for model in models:
                    await model.insert()
            else:
                await cls.database.execute(
                    cls.table.insert(),
                    [model.dict(by_alias=True) for model in models],
                )
            return None
        raise ModelMissingError("You must give at least one model to insert")

    @classmethod
    async def save_many(cls, *models: Self):
        """save many models into database"""
        if models:
            for model in models:
                await model.save()
            return None
        raise ModelMissingError("You must give at least one model to save")

    @classmethod
    async def delete_many(cls, *models: Self) -> int:
        """delete many models from database"""
        if models:
            result = await cls.database.execute(
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
    def filter(cls, *args: Any) -> QuerySet[Self]:
        """query with any filter condition"""
        return QuerySet(cls, filter=args)

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
    async def get(cls, *args: Any) -> Self:
        """select one model with filter condition, if not exist, raise error"""
        return await cls.filter(*args).get()

    @classmethod
    async def get_or_none(cls, *args: Any) -> Optional[Self]:
        """select one model with filter condition, if not exist, return None"""
        try:
            return await cls.filter(*args).get()
        except NoMatchDataError:
            return None

    @classmethod
    async def get_or_create(
        cls,
        *args: Any,
        defaults: Optional[Dict[str, Any]] = None,
    ) -> Self:
        """select one model with filter condition, if not exist, create one"""
        try:
            return await cls.filter(*args).get()
        except NoMatchDataError:
            create_values = {
                arg.left.name: arg.right.value
                for arg in args
                if isinstance(arg, ColumnElement)
            }
            create_values.update(
                {
                    (k.name if isinstance(k, Column) else k): v
                    for k, v in (defaults or {}).items()
                },
            )
            return await cls(**create_values).insert()

    @classmethod
    async def update_or_create(
        cls,
        *args: Any,
        defaults: Optional[Dict[str, Any]] = None,
    ) -> Self:
        """update one model with filter condition,
        if not exist, create one with filter and defaults values"""
        try:
            model = await cls.filter(*args).get()
            return await model.update(**(defaults or {}))
        except NoMatchDataError:
            create_values = {
                arg.left.name: arg.right.value
                for arg in args
                if isinstance(arg, ColumnElement)
            }
            create_values.update(
                {
                    (k.name if isinstance(k, Column) else k): v
                    for k, v in (defaults or {}).items()
                },
            )
            return await cls(**create_values).insert()

    @property
    def pk_filter(self) -> Tuple[ColumnElement[bool], ...]:
        """generate primary key filter condition"""
        return tuple(
            getattr(self.__class__, pk) == getattr(self, pk)
            for pk in self.__meta__.primary_key
        )

    @classmethod
    def get_pk_columns(cls) -> Tuple[Column, ...]:
        """get primary key columns"""
        return tuple(getattr(cls, pk) for pk in cls.__meta__.primary_key)

    @classmethod
    def parse_from_db_dict(cls, data: Dict[str, Any]) -> Self:
        """parse model from database result dict"""
        model = cls.parse_obj(data)
        for foreign_key in cls.__meta__.foreign_keys:
            model.__foreign_key_values__[foreign_key] = data.pop(foreign_key, None)
        return model

    def update_from_dict(self, update_data: Mapping[Any, Any]):
        """update model from dict"""
        for k, v in update_data.items():
            if k in self.__fields__:
                setattr(self, k, v)
            elif k in self.__meta__.foreign_keys:
                self.__foreign_key_values__[k] = v

    def update_from_kwargs(self, **kwargs: Any):
        """update model from kwargs"""
        for k, v in kwargs.items():
            setattr(self, k, v)

    def _extract_db_fields(self, exclude_pk: bool = False) -> Dict[str, Any]:
        """extract database fields from model"""
        exclude = (
            self.__meta__.related_fields.keys()
            | self.__meta__.reverse_related_fields.keys()
        )
        if exclude_pk:
            exclude |= set(self.__meta__.primary_key)
        data = self.dict(by_alias=True, exclude=exclude)
        for field_name, field in self.__meta__.related_fields.items():
            value = getattr(
                getattr(self, field_name),
                field.foreign_key,
            )
            data[field.foreign_key_self_name] = value
            self.__foreign_key_values__[field.foreign_key_self_name] = value
            if not field.nullable and not data[field.foreign_key_self_name]:
                raise ForeignKeyMissingError(
                    (
                        "Foreign key field"
                        f" {self.tablename}.{field.foreign_key_self_name}cannot be None"
                        " when insert or update"
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
                (ReverseRelationshipField, ForeignKeyField),
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
    def _generate_sqlalchemy_column(cls):
        if any(f for f in cls.__fields__.values() if isinstance(f.type_, ForwardRef)):
            cls.update_forward_refs()
        for model_field in cls.__fields__.values():
            field_info = model_field.field_info
            if isinstance(field_info, BaseField):
                cls.__meta__.columns[model_field.name] = Column(
                    model_field.name,
                    type_=get_sqlalchemy_type_from_field(model_field),
                    primary_key=field_info.primary_key,
                    nullable=field_info.nullable,
                    index=field_info.index,
                    unique=field_info.unique,
                    autoincrement=field_info.autoincrement,
                    default=field_info.default or field_info.default_factory or None,
                    **field_info.sa_column_args,
                )
                setattr(cls, model_field.name, cls.__meta__.columns[model_field.name])
            elif isinstance(field_info, ForeignKeyField):
                if field_info.related_field_name is None:
                    for rname, rfield in field_info.related_model.__fields__.items():
                        if (
                            isinstance(rfield.field_info, ReverseRelationshipField)
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
                    ),
                    nullable=field_info.nullable,
                )
                cls.__meta__.related_fields[model_field.name] = field_info
                setattr(cls, model_field.name, cls.__meta__.columns[model_field.name])
            elif isinstance(field_info, ReverseRelationshipField):
                # from pydantic.fields.py
                field_info.is_list = model_field.shape in (2, 3, 6, 7, 8, 9)
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
                    setattr(cls, model_field.name, field_info.related_model)
                else:
                    raise RelationSolveError(
                        (
                            "There are no related fields associated with"
                            f" {cls}.{model_field.name}"
                        ),
                    )
            elif isinstance(field_info, ManyToManyField):
                if model_field.shape not in (2, 3, 6, 7, 8, 9):
                    raise FieldTypeError(
                        (
                            'ManyToManyField must be a iterable "cherry.Model" type,'
                            ' such as list[Model]'
                        ),
                    )
                if not hasattr(field_info, "many_to_many_key"):
                    if len(field_info.related_model.__meta__.primary_key) != 1:
                        raise PrimaryKeyMultipleError(
                            (
                                f'{cls} has multiple primary keys, you must'
                                ' explicitly give out foreign key through'
                                ' Relationship(foreign_key="some field")'
                            ),
                        )
                    field_info.m2m_field = (
                        field_info.related_model.__meta__.primary_key[0]
                    )
                if not hasattr(field_info, "related_model"):
                    for rname, rfield in field_info.related_model.__fields__.items():
                        if (
                            isinstance(rfield.field_info, ManyToManyField)
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
                cls.__meta__.many_to_many_fields[model_field.name] = field_info
        cls.__meta__.foreign_keys = tuple(
            f.foreign_key_self_name for f in cls.__meta__.related_fields.values()
        )
        cls.__meta__.primary_key = tuple(
            field.name
            for field in cls.__fields__.values()
            if isinstance(field.field_info, BaseField) and field.field_info.primary_key
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
                field.m2m_table_field = f"{cls.tablename}_{field.m2m_field}"
                field.related_field.m2m_table_field = (
                    f"{field.related_model.tablename}_{field.related_field.m2m_field}"
                )
                table = Table(
                    f"{cls.tablename}_and_{field.related_model.tablename}",
                    metadata,
                    Column(
                        field.m2m_table_field,
                        ForeignKey(
                            f"{cls.tablename}.{field.m2m_field}",
                            onupdate=field.on_update
                            or (field.related_field and field.related_field.on_update)
                            or "NO ACTION",
                            ondelete=field.on_delete
                            or (field.related_field and field.related_field.on_update)
                            or "NO ACTION",
                        ),
                    ),
                    Column(
                        field.related_field.m2m_table_field,
                        ForeignKey(
                            f"{field.related_model.tablename}.{field.related_field.m2m_field}",
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

        return cls.table
