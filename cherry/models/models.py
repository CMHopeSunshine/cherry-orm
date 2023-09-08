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

from cherry.fields.fields import (
    BaseField,
    ForeignKeyField,
    ManyToManyField,
    ReverseRelationshipField,
)
from cherry.fields.types import get_sqlalchemy_type_from_field
from cherry.meta.meta import init_meta_config, MetaConfig, mix_meta_config
from cherry.meta.pydantic_config import generate_pydantic_config
from cherry.queryset.queryset import QuerySet
from cherry.utils import check_is_list

from .decorator import check_connected

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

        for _field_name, model_field in new_cls.__fields__.items():
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
                raise TypeError(
                    (
                        'Field Type must be "cherry.Field", got unexpected type: '
                        f' {field_info.__class__.__name__}'
                    ),
                )
        meta_config.primary_key = tuple(
            field.name
            for field in new_cls.__fields__.values()
            if isinstance(field.field_info, BaseField) and field.field_info.primary_key
        )

        if not meta_config.abstract and hasattr(meta_config, "database"):
            meta_config.database.add_model(new_cls)

        return new_cls


class Model(BaseModel, metaclass=ModelMeta):
    if TYPE_CHECKING:
        __meta__: ClassVar[Type[MetaConfig]]

    __foreign_key_values__: Dict[str, Any] = PrivateAttr(default_factory=dict)

    @check_connected
    async def insert(self) -> Self:
        """将对象插入到数据库

        如果主键为数据库自增主键，则会更新主键

        返回:
            Self: 返回插入后的对象
        """
        result = await self.__meta__.database.execute(
            self.__meta__.table.insert().values(
                **self._extract_db_fields(),
            ),
        )
        if result.inserted_primary_key:
            self.update_from_dict(result.inserted_primary_key._asdict())
        return self

    @check_connected
    async def update(self, **kwargs: Any) -> Self:
        self.update_from_dict(kwargs)
        if self._check_pk_null():
            raise ValueError("Primary key can not be null when update")
        await self.__meta__.database.execute(
            self.__meta__.table.update()
            .values(**self._extract_db_fields(exclude_pk=True))
            .where(*self.pk_filter),
        )
        return self

    @check_connected
    async def fetch(self) -> Self:
        result = await self.__meta__.database.execute(
            self.__meta__.table.select().where(*self.pk_filter),
        )
        if result_one := result.fetchone():
            self.update_from_dict(result_one._asdict())
        return self

    @check_connected
    async def fetch_related(self, *tables: Any) -> Self:
        if tables:
            table_names = []
            for table in tables:
                if isinstance(table, Table):
                    table_names.append(table.name)
                elif issubclass(table, Model):
                    table_names.append(table.__meta__.tablename)
                elif isinstance(table, str):
                    table_names.append(table)
                else:
                    raise TypeError(
                        f"table must be str, Table or Model, not {type(table)}",
                    )
        else:
            table_names = None

        related_fields = {
            name: field
            for name, field in self.__meta__.related_fields.items()
            if table_names is None
            or field.related_model.__meta__.tablename in table_names
        }
        for name, rfield in related_fields.items():
            if rfield.foreign_key_self_name not in self.__foreign_key_values__:
                raise ValueError(
                    (
                        "Can not fetch related model if not been inserted into or"
                        " fetched from database"
                    ),
                )
            related_data = await rfield.related_model.__meta__.database.execute(
                rfield.related_model.__meta__.table.select().where(
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
                    raise ValueError(
                        f"No matching data for {self.__class__.__name__}.{name}",
                    )

        reverse_related_fields = {
            name: field
            for name, field in self.__meta__.reverse_related_fields.items()
            if table_names is None
            or field.related_model.__meta__.tablename in table_names
        }

        for name, rfield in reverse_related_fields.items():
            related_data = await rfield.related_model.__meta__.database.execute(
                rfield.related_model.__meta__.table.select().where(
                    getattr(
                        rfield.related_model,
                        rfield.related_field_name,
                    )
                    == getattr(self, rfield.related_field.foreign_key),
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
                        raise ValueError(
                            f"No matching data for {self.__class__.__name__}.{name}",
                        )
        return self

    @check_connected
    async def save(self) -> Self:
        fetch = await self.__meta__.database.execute(
            self.__meta__.table.select().where(*self.pk_filter),
        )
        if fetch:
            await self.update()
        else:
            return await self.insert()
        return self

    @check_connected
    async def delete(self) -> Self:
        await self.__meta__.database.execute(
            self.__meta__.table.delete().where(*self.pk_filter),
        )
        return self

    @classmethod
    @check_connected
    async def insert_many(cls, *models: Self, need_pk_update: bool = False):
        if models:
            if need_pk_update:
                for model in models:
                    await model.insert()
            else:
                await cls.__meta__.database.execute(
                    cls.__meta__.table.insert(),
                    [model.dict(by_alias=True) for model in models],
                )
            return None
        raise ValueError("No models to create")

    @classmethod
    @check_connected
    async def save_many(cls, *models: Self):
        if models:
            for model in models:
                await model.save()
            return None
        raise ValueError("No models to save")

    @classmethod
    @check_connected
    async def delete_many(cls, *models: Self) -> int:
        if models:
            result = await cls.__meta__.database.execute(
                cls.__meta__.table.delete(),
                [model.dict(by_alias=True) for model in models],
            )
            return result.rowcount
        raise ValueError("No models to delete")

    @classmethod
    @check_connected
    def query(cls) -> QuerySet[Self]:
        return QuerySet(cls)

    @classmethod
    @check_connected
    def filter(cls, *args: Any) -> QuerySet[Self]:
        return QuerySet(cls, filter=args)

    @classmethod
    @check_connected
    def select_related(cls, *args: Any) -> QuerySet[Self]:
        return QuerySet(cls).prefetch_related(*args)

    @classmethod
    @check_connected
    async def paginate(cls, page: int, page_size: int) -> List[Self]:
        return await QuerySet(cls).paginate(page, page_size)

    @classmethod
    @check_connected
    async def first(cls) -> Optional[Self]:
        return await QuerySet(cls).first()

    @classmethod
    @check_connected
    async def all(cls) -> List[Self]:
        return await QuerySet(cls).all()

    @classmethod
    @check_connected
    async def random_one(cls) -> Optional[Self]:
        return await QuerySet(cls).random_one()

    @classmethod
    @check_connected
    async def get(cls, *args: Any) -> Optional[Self]:
        return await cls.filter(*args).first()

    @classmethod
    @check_connected
    async def get_or_none(cls, *args: Any) -> Optional[Self]:
        return await cls.filter(*args).first()

    @classmethod
    @check_connected
    async def get_or_create(
        cls,
        defaults: Optional[Dict[str, Any]],
        *args: Any,
    ) -> Self:
        if model := await cls.filter(*args).first():
            return model
        defaults = {
            arg.left.name: arg.left.value
            for arg in args
            if isinstance(arg, ColumnElement)
        }
        defaults.update(
            {
                (k.name if isinstance(k, Column) else k): v
                for k, v in (defaults or {}).items()
            },
        )
        return await cls(**defaults).insert()

    @classmethod
    @check_connected
    async def update_or_create(
        cls,
        defaults: Optional[Dict[str, Any]],
        *args: Any,
    ) -> Self:
        if model := await cls.filter(*args).first():
            return await model.update(**(defaults or {}))
        defaults = {
            arg.left.name: arg.left.value
            for arg in args
            if isinstance(arg, ColumnElement)
        }
        defaults.update(
            {
                (k.name if isinstance(k, Column) else k): v
                for k, v in (defaults or {}).items()
            },
        )
        return await cls(**defaults).insert()

    @property
    def pk_filter(self) -> Tuple[ColumnElement[bool], ...]:
        """生成主键查询表达式

        返回:
            Tuple[ColumnElement[bool], ...]: 主键查询表达式
        """
        return tuple(
            getattr(self.__class__, pk) == getattr(self, pk)
            for pk in self.__meta__.primary_key
        )

    @classmethod
    def get_pk_columns(cls) -> Tuple[Column, ...]:
        """获取主键列

        返回:
            Tuple[Column, ...]: 主键列
        """
        return tuple(getattr(cls, pk) for pk in cls.__meta__.primary_key)

    @classmethod
    def parse_from_db_dict(cls, data: Dict[str, Any]) -> Self:
        model = cls.parse_obj(data)
        for foreign_key in cls.__meta__.foreign_keys:
            model.__foreign_key_values__[foreign_key] = data.pop(foreign_key, None)
        return model

    def update_from_dict(self, update_data: Mapping[Any, Any]):
        for k, v in update_data.items():
            if k in self.__fields__:
                setattr(self, k, v)
            elif k in self.__meta__.foreign_keys:
                self.__foreign_key_values__[k] = v

    def update_from_kwargs(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def _extract_db_fields(self, exclude_pk: bool = False) -> Dict[str, Any]:
        """从模型中提取出要存储到数据库中的字段

        返回:
            Dict[str, Any]: 模型的数据库字段
        """
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
                raise ValueError(
                    (
                        f"Field {field.foreign_key_self_name} of "
                        f"{self.__meta__.tablename} cannot be null"
                    ),
                )
        return data

    def _check_pk_null(self) -> bool:
        return all(getattr(self, pk) is None for pk in self.__meta__.primary_key)

    @classmethod
    def update_forward_refs(cls, **localns: Any):
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
                    raise TypeError("Related model must be a Model")
                if field_info.related_model in model_type:
                    raise ValueError("同一个模型只有有一个关联关系")
                model_type.append(field_info.related_model)

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
                        raise ValueError("主键多于一个，你必须手动给出主键")
                    field_info.foreign_key = (
                        field_info.related_model.__meta__.primary_key[0]
                    )
                field_info.foreign_key_self_name = f"{field_info.related_model.__meta__.tablename}_{field_info.foreign_key}"  # noqa: E501
                cls.__meta__.columns[model_field.name] = Column(
                    f"{field_info.related_model.__meta__.tablename}_{field_info.foreign_key}",
                    ForeignKey(
                        f"{field_info.related_model.__meta__.tablename}.{field_info.foreign_key}",
                    ),
                    nullable=field_info.nullable,
                )
                cls.__meta__.related_fields[model_field.name] = field_info
                setattr(cls, model_field.name, cls.__meta__.columns[model_field.name])
            elif isinstance(field_info, ReverseRelationshipField):
                field_info.is_list = check_is_list(model_field.outer_type_)
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
                    raise ValueError("关联字段不存在")
            elif isinstance(field_info, ManyToManyField):
                ...
        cls.__meta__.foreign_keys = tuple(
            f.foreign_key_self_name for f in cls.__meta__.related_fields.values()
        )
        return cls.__meta__.columns

    @classmethod
    def _generate_sqlalchemy_table(cls, metadata: MetaData) -> Table:
        if cls.__meta__.abstract:
            raise ValueError("Can not generate table for abstract model")
        if hasattr(cls.__meta__, "table"):
            return cls.__meta__.table
        cls.__meta__.metadata = metadata
        cls.__meta__.table = Table(
            cls.__meta__.tablename,
            metadata,
            *cls.__meta__.columns.values(),
            *cls.__meta__.constraints,
        )
        return cls.__meta__.table
