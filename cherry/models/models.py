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

from cherry.fields.annotated import FieldInfoEnum
from cherry.fields.fields import (
    BaseField,
    ForeignKeyField,
    RelationshipField,
)
from cherry.meta.meta import init_meta_config, MetaConfig, mix_meta_config
from cherry.meta.pydantic_config import generate_pydantic_config
from cherry.queryset.queryset import QuerySet
from cherry.utils import check_is_list, get_annotated_field_info

from .decorator import check_connected

from pydantic import PrivateAttr
from pydantic.fields import Field, FieldInfo
from pydantic.main import BaseModel, ModelMetaclass
from sqlalchemy import Column, ForeignKey, Table
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
        annotated_info = {}
        for ann_name, ann in attrs.get("__annotations__", {}).items():
            annotated_info[ann_name] = get_annotated_field_info(ann)

        new_cls = cast(Type["Model"], super().__new__(cls, name, bases, attrs))

        meta_config = new_cls.__meta__

        for field_name, model_field in new_cls.__fields__.items():
            field_info = model_field.field_info

            if field_info.__class__ is FieldInfo:
                field_info = BaseField.from_base_field_info(field_info)
            if isinstance(field_info, BaseField):
                # TODO: 重新改为Undefine
                if field_info.name is None:
                    field_info.name = field_name
                if field_info.type is None:
                    field_info.type = model_field.type_
                if FieldInfoEnum.primary_key in annotated_info[field_name]:
                    field_info.primary_key = True
                    field_info.nullable = False
                if FieldInfoEnum.autoincrement in annotated_info[field_name]:
                    field_info.autoincrement = True
                if FieldInfoEnum.index in annotated_info[field_name]:
                    field_info.index = True
                if FieldInfoEnum.unique in annotated_info[field_name]:
                    field_info.unique = True
                if field_info.nullable is None and model_field.allow_none:
                    field_info.nullable = True
            elif isinstance(field_info, (RelationshipField, ForeignKeyField)):
                if not (
                    isinstance(
                        model_field.type_,
                        ForwardRef,
                    )
                    or issubclass(model_field.type_, Model)
                ):
                    raise TypeError("Related model type must be a Model")
                if model_field.allow_none:
                    field_info.nullable = True
                field_info.related_model = model_field.type_  # type: ignore
                if isinstance(field_info, ForeignKeyField):
                    field_info.foreign_key_self_name = field_info.foreign_key.replace(
                        ".",
                        "_",
                    )
                    meta_config.related_fields[field_name] = field_info
                    meta_config.columns[field_name] = Column(
                        field_info.foreign_key_self_name,
                        ForeignKey(
                            field_info.foreign_key,
                        ),
                        nullable=field_info.nullable,
                    )
                else:
                    field_info.is_list = check_is_list(model_field.outer_type_)
                    meta_config.back_related_fields[field_name] = field_info
            else:
                raise ValueError(f"Invalid field_info: {field_info}")
            meta_config.model_fields[field_name] = field_info
        meta_config.primary_key = tuple(
            field.name
            for field in meta_config.model_fields.values()
            if isinstance(field, BaseField)
            and field.primary_key
            and field.name is not None
        )
        meta_config.foreign_keys = tuple(
            f.foreign_key_self_name for f in meta_config.related_fields.values()
        )

        if not meta_config.abstract and hasattr(meta_config, "database"):
            meta_config.columns.update(
                {
                    k: v.to_sqlalchemy_column()
                    for k, v in meta_config.model_fields.items()
                    if isinstance(v, BaseField)
                },
            )
            meta_config.table = Table(
                new_cls.__meta__.tablename,
                new_cls.__meta__.database._metadata,
                *meta_config.columns.values(),
                *meta_config.constraints,
            )
            meta_config.metadata = new_cls.__meta__.database._metadata

        return new_cls

    def __getattr__(self, item: str) -> Any:
        if item in self.__meta__.columns:
            return self.__meta__.columns[item]
        if item in self.__meta__.related_fields:
            return self.__meta__.related_fields[item].related_model
        if item in self.__meta__.back_related_fields:
            return self.__meta__.back_related_fields[item].related_model
        return super().__getattribute__(item)


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
                    getattr(rfield.related_model, rfield.foreign_key_field_name)
                    == self.__foreign_key_values__[rfield.foreign_key_self_name],
                ),
            )
            if related_one := related_data.fetchone():
                setattr(
                    self,
                    name,
                    rfield.related_model.parse_from_db_dict(related_one._asdict()),
                )

        back_related_fields = {
            name: field
            for name, field in self.__meta__.back_related_fields.items()
            if table_names is None
            or field.related_model.__meta__.tablename in table_names
        }

        for name, rfield in back_related_fields.items():
            target_field = rfield.related_model.__meta__.related_fields[
                rfield.related_field
            ]
            related_data = await rfield.related_model.__meta__.database.execute(
                rfield.related_model.__meta__.table.select().where(
                    getattr(
                        rfield.related_model,
                        rfield.related_field,
                    )
                    == getattr(self, target_field.foreign_key_field_name),
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
            | self.__meta__.back_related_fields.keys()
        )
        if exclude_pk:
            exclude |= set(self.__meta__.primary_key)
        data = self.dict(by_alias=True, exclude=exclude)
        for field_name, field in self.__meta__.related_fields.items():
            value = getattr(
                getattr(self, field_name),
                field.foreign_key_field_name,
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
        super().update_forward_refs()
        for _, field in cls.__fields__.items():
            field_info = field.field_info
            if isinstance(
                field_info,
                (RelationshipField, ForeignKeyField),
            ) and isinstance(field_info.related_model, ForwardRef):
                field_info.related_model = field.type_
