from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    overload,
    Tuple,
    Type,
    TYPE_CHECKING,
    TypeVar,
    Union,
)
from typing_extensions import Self, TypeVarTuple, Unpack

from cherry.exception import MultipleDataError, NoMatchDataError, PaginateArgError
from cherry.fields.fields import (
    ForeignKeyField,
    ManyToManyField,
    ReverseRelationshipField,
)
from cherry.fields.utils import validate_fields

from .protocol import QuerySetProtocol

from sqlalchemy import Column, ColumnElement, exists, func, Select, select

if TYPE_CHECKING:
    from cherry.models.models import Model

T_MODEL = TypeVar("T_MODEL", bound="Model")
T = TypeVar("T")
Ts = TypeVarTuple("Ts")


@dataclass
class QueryOptions:
    filter: List[Any] = field(default_factory=list)
    order_by: List[Any] = field(default_factory=list)
    limit: Optional[int] = None
    offset: Optional[int] = None
    related: List[Any] = field(default_factory=list)
    join: List[Any] = field(default_factory=list)
    related_fields: Dict[str, ForeignKeyField] = field(default_factory=dict)
    reverse_related_fields: Dict[str, ReverseRelationshipField] = field(
        default_factory=dict,
    )
    many_to_many_fields: Dict[str, ManyToManyField] = field(default_factory=dict)

    def as_select_option(self, select_stat: Select):
        select_stat = select_stat.where(*self.filter)
        if self.order_by:
            select_stat = select_stat.order_by(*self.order_by)
        if self.limit:
            select_stat = select_stat.limit(self.limit)
        if self.offset:
            select_stat = select_stat.offset(self.offset)
        if self.join:
            select_stat = select_stat.join(*self.join)
        return select_stat


class QuerySet(QuerySetProtocol, Generic[T_MODEL]):
    def __init__(
        self,
        model_cls: Type[T_MODEL],
        filter: Optional[Tuple[Any, ...]] = None,
        order_by: Optional[Tuple[Any, ...]] = None,
        limit: Optional[int] = None,
    ) -> None:
        self.model_cls = model_cls
        filter_ = list(filter or [])
        join_ = []
        for f in filter_:
            if isinstance(f, ColumnElement):
                if (
                    isinstance(f.left, Column)
                    and f.left.table != self.model_cls.__meta__.table
                ):
                    join_.append(f.left.table)
                if (
                    isinstance(f.right, Column)
                    and f.right.table != self.model_cls.__meta__.table
                ):
                    join_.append(f.right.table)
        self.options = QueryOptions(
            filter=filter_,
            order_by=list(order_by or []),
            limit=limit,
            join=join_,
        )

    def filter(self, *args: Any) -> Self:
        for f in args:
            if isinstance(f, ColumnElement):
                if (
                    isinstance(f.left, Column)
                    and f.left.table != self.model_cls.__meta__.table
                ):
                    self.options.join.append(f.left.table)
                if (
                    isinstance(f.right, Column)
                    and f.right.table != self.model_cls.__meta__.table
                ):
                    self.options.join.append(f.right.table)
        self.options.filter.extend(args)
        return self

    def order_by(self, *args: Any) -> Self:
        self.options.order_by.extend(args)
        return self

    def limit(self, num: int) -> Self:
        self.options.limit = num
        return self

    def offset(self, num: int) -> Self:
        self.options.offset = num
        return self

    def prefetch_related(self, *args: Any) -> Self:
        table_names = self.model_cls._get_related_tables(*args)

        self.options.related_fields = (
            self.model_cls.__meta__.related_fields
            if table_names is None
            else {
                name: field
                for name, field in self.model_cls.__meta__.related_fields.items()
                if field.related_model.__meta__.tablename in table_names
            }
        )
        reverse_related_fields = self.model_cls.__meta__.reverse_related_fields
        self.options.reverse_related_fields = (
            self.model_cls.__meta__.reverse_related_fields
            if table_names is None
            else {
                name: field
                for name, field in reverse_related_fields.items()
                if field.related_model.__meta__.tablename in table_names
            }
        )
        self.options.many_to_many_fields = (
            self.model_cls.__meta__.many_to_many_fields
            if table_names is None
            else {
                name: field
                for name, field in self.model_cls.__meta__.many_to_many_fields.items()
                if field.related_model.__meta__.tablename in table_names
            }
        )
        return self

    @overload
    def values(
        self,
        *args: Unpack[Tuple[T, ...]],
        flatten: Literal[True],
    ) -> "ValueQuerySet[T]":
        ...

    @overload
    def values(
        self,
        *args: Unpack[Tuple[T, Unpack[Ts]]],
        flatten: Literal[False] = False,
    ) -> "ValuesQuerySet[T, Unpack[Ts]]":
        ...

    def values(
        self,
        *args: Unpack[Tuple[T, Unpack[Ts]]],
        flatten: bool = False,
    ) -> Union["ValuesQuerySet[T, Unpack[Ts]]", "ValueQuerySet[T]"]:
        if flatten:
            if len(args) > 1:
                raise ValueError("Only one argument is allowed")
            return ValueQuerySet(
                args[0],
                model_cls=self.model_cls,
                options=self.options,
            )
        return ValuesQuerySet(*args, model_cls=self.model_cls, options=self.options)

    def value_dict(self, *args: Any) -> "ValueDictQuerySet":
        return ValueDictQuerySet(
            *args,
            model_cls=self.model_cls,
            options=self.options,
        )

    def coalesce(
        self,
        *column: Unpack[Ts],
    ) -> "CoalesceQuerySet[Unpack[Ts]]":
        return CoalesceQuerySet(*column, model_cls=self.model_cls, options=self.options)

    async def first(self) -> Optional[T_MODEL]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(self.model_cls.table.select()),
        )
        if result_one := result.fetchone():
            data = result_one._asdict()
            await self._fetch_one_related(data)

            return self.model_cls.parse_from_db_dict(data)

        return None

    async def get(self) -> T_MODEL:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(self.model_cls.table.select()),
        )
        results = result.fetchall()
        if len(results) > 1:
            raise MultipleDataError(
                f"{self.model_cls} expect one data, but got {len(results)} datas",
            )
        if len(results) == 1:
            data = results[0]._asdict()
            await self._fetch_one_related(data)
            return self.model_cls.parse_from_db_dict(data)
        raise NoMatchDataError(f"No match data for {self.model_cls}")

    async def all(self) -> List[T_MODEL]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(self.model_cls.table.select()),
        )
        data = [data._asdict() for data in result.fetchall()]
        await self._fetch_many_related(data)

        return [self.model_cls.parse_from_db_dict(data) for data in data]

    async def random_one(self) -> Optional[T_MODEL]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(
                self.model_cls.table.select().order_by(func.random()),
            ),
        )
        if result_one := result.fetchone():
            data = result_one._asdict()
            await self._fetch_one_related(data)
            return self.model_cls.parse_from_db_dict(data)
        return None

    async def paginate(self, page: int, page_size: int) -> List[T_MODEL]:
        if page < 1 or page_size < 1:
            raise PaginateArgError("page and page_size must be positive")
        self.options.limit = page_size
        self.options.offset = (page - 1) * page_size
        return await self.all()

    async def delete(self) -> int:
        result = await self.model_cls.database.execute(
            self.model_cls.table.delete().where(*self.options.filter),
        )
        return result.rowcount

    async def update(self, **kwargs: Any) -> int:
        values = validate_fields(self.model_cls, kwargs)
        result = await self.model_cls.database.execute(
            self.model_cls.table.update().values(**values),
        )
        return result.rowcount

    async def count(self) -> int:
        result = await self.model_cls.database.execute(
            select(func.count())
            .select_from(self.model_cls.table)
            .where(*self.options.filter),
        )
        return result.scalar()  # type: ignore

    async def exists(self) -> bool:
        result = await self.model_cls.database.execute(
            select(
                exists().select_from(self.model_cls.table).where(*self.options.filter),
            ),
        )
        return result.scalar()  # type: ignore

    async def max(self, column: T) -> Optional[T]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(func.max(column))),
        )
        return result.scalar()

    async def min(self, column: T) -> Optional[T]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(func.min(column))),
        )
        return result.scalar()

    async def avg(self, column: T) -> Optional[T]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(func.avg(column))),
        )
        return result.scalar()

    async def sum(self, column: T) -> Optional[T]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(func.sum(column))),
        )
        return result.scalar()

    async def _fetch_one_related(self, now_data: Dict[str, Any]):
        for name, rfield in self.options.related_fields.items():
            related_data = await rfield.related_model.__meta__.database.execute(
                rfield.related_model.__meta__.table.select().where(
                    getattr(rfield.related_model, rfield.foreign_key)
                    == now_data[rfield.foreign_key_self_name],
                ),
            )
            if related_one := related_data.fetchone():
                now_data[name] = related_one._asdict()
        for name, rfield in self.options.reverse_related_fields.items():
            target_field = rfield.related_field
            related_data = await rfield.related_model.__meta__.database.execute(
                rfield.related_model.__meta__.table.select().where(
                    getattr(
                        rfield.related_model,
                        rfield.related_field_name,
                    )
                    == now_data[target_field.foreign_key],
                ),
            )
            if rfield.is_list:
                now_data[name] = [
                    related_one._asdict() for related_one in related_data.fetchall()
                ]
            else:
                if related_one := related_data.fetchone():
                    now_data[name] = related_one._asdict()
        for name, rfield in self.options.many_to_many_fields.items():
            related_data = await self.model_cls.database.execute(
                rfield.table.select().where(
                    getattr(
                        rfield.table.c,
                        rfield.m2m_table_field,
                    )
                    == getattr(self.model_cls, rfield.m2m_field),
                ),
            )
            now_data[name] = [
                related_one._asdict() for related_one in related_data.fetchall()
            ]

    async def _fetch_many_related(self, now_datas: List[Dict[str, Any]]):
        for name, rfield in self.options.related_fields.items():
            related_values = [data[rfield.foreign_key_self_name] for data in now_datas]
            related_data = await rfield.related_model.__meta__.database.execute(
                rfield.related_model.__meta__.table.select().where(
                    getattr(rfield.related_model, rfield.foreign_key).in_(
                        related_values,
                    ),
                ),
            )
            related_datas = [rd._asdict() for rd in related_data.fetchall()]
            related_datas_dict = {
                data[rfield.foreign_key]: data for data in related_datas
            }
            for data in now_datas:
                data[name] = related_datas_dict.get(
                    data[rfield.foreign_key_self_name],
                    None,
                )
                if data[name] is None and not rfield.nullable:
                    raise NoMatchDataError(
                        f"No matching data for {self.model_cls}.{name}",
                    )
        for name, rfield in self.options.reverse_related_fields.items():
            target_field = rfield.related_field
            related_values = [data[target_field.foreign_key] for data in now_datas]
            related_data = await rfield.related_model.__meta__.database.execute(
                rfield.related_model.__meta__.table.select().where(
                    getattr(
                        rfield.related_model,
                        rfield.related_field_name,
                    ).in_(related_values),
                ),
            )
            related_datas = [rd._asdict() for rd in related_data.fetchall()]
            for data in now_datas:
                rd = [
                    related_data
                    for related_data in related_datas
                    if related_data[target_field.foreign_key_self_name]
                    == data[target_field.foreign_key]
                ]
                if rfield.is_list:
                    data[name] = rd
                elif rd:
                    data[name] = rd[0]
        for name, rfield in self.options.many_to_many_fields.items():
            related_values = [data[rfield.m2m_field] for data in now_datas]
            related_data = await self.model_cls.database.execute(
                rfield.table.select().where(
                    getattr(
                        rfield.table.c,
                        rfield.m2m_table_field,
                    ).in_(related_values),
                ),
            )
            related_datas = [rd._asdict() for rd in related_data.fetchall()]
            for data in now_datas:
                data[name] = [
                    related_data
                    for related_data in related_datas
                    if related_data[rfield.m2m_table_field] == data[rfield.m2m_field]
                ]


class ValuesQuerySet(QuerySetProtocol, Generic[T, Unpack[Ts]]):
    def __init__(
        self,
        query1: T,
        *querys: Unpack[Ts],
        model_cls: Type[T_MODEL],
        options: QueryOptions,
    ) -> None:
        self.query1 = query1
        self.querys = querys
        self.model_cls = model_cls
        self.options = options

    async def first(self) -> Optional[Tuple[T, Unpack[Ts]]]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(self.query1, *self.querys)),
        )
        if result_one := result.fetchone():
            return result_one._tuple()
        return None

    async def get(self) -> Tuple[T, Unpack[Ts]]:
        results = await self.all()
        if len(results) > 1:
            raise MultipleDataError(
                f"{self.model_cls} expect one data, but got {len(results)} datas",
            )
        if len(results) == 1:
            return results[0]
        raise NoMatchDataError(f"No match data for {self.model_cls}")

    async def all(self) -> List[Tuple[T, Unpack[Ts]]]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(self.query1, *self.querys)),
        )
        return [result_one._tuple() for result_one in result.fetchall()]

    async def random_one(self) -> Optional[Tuple[T, Unpack[Ts]]]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(
                select(self.query1, *self.querys).order_by(func.random()),
            ),
        )
        if result_one := result.fetchone():
            return result_one._tuple()
        return None

    async def paginate(self, page: int, page_size: int) -> List[Tuple[T, Unpack[Ts]]]:
        if page < 1 or page_size < 1:
            raise PaginateArgError("page and page_size must be positive")
        self.options.limit = page_size
        self.options.offset = (page - 1) * page_size
        return await self.all()


class ValueQuerySet(QuerySetProtocol, Generic[T]):
    def __init__(
        self,
        query: T,
        model_cls: Type[T_MODEL],
        options: QueryOptions,
    ) -> None:
        self.query = query
        self.model_cls = model_cls
        self.options = options

    async def first(self) -> Optional[T]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(self.query)),
        )
        if result_one := result.fetchone():
            return result_one._tuple()[0]
        return None

    async def get(self) -> T:
        results = await self.all()
        if len(results) > 1:
            raise MultipleDataError(
                f"{self.model_cls} expect one data, but got {len(results)} datas",
            )
        if len(results) == 1:
            return results[0]
        raise NoMatchDataError(f"No match data for {self.model_cls}")

    async def all(self) -> List[T]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(self.query)),
        )
        return [result_one._tuple()[0] for result_one in result.fetchall()]

    async def random_one(self) -> Optional[T]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(self.query)).order_by(func.random()),
        )
        if result_one := result.fetchone():
            return result_one._tuple()[0]
        return None

    async def paginate(self, page: int, page_size: int) -> List[T]:
        if page < 1 or page_size < 1:
            raise PaginateArgError("page and page_size must be positive")
        self.options.limit = page_size
        self.options.offset = (page - 1) * page_size
        return await self.all()


class ValueDictQuerySet(QuerySetProtocol):
    def __init__(
        self,
        *querys: Any,
        model_cls: Type[T_MODEL],
        options: QueryOptions,
    ) -> None:
        self.querys = querys
        self.model_cls = model_cls
        self.options = options

    async def first(self) -> Optional[Dict[str, Any]]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(*self.querys)),
        )
        if result_one := result.fetchone():
            return result_one._asdict()
        return None

    async def get(self) -> Dict[str, Any]:
        results = await self.all()
        if len(results) > 1:
            raise MultipleDataError(
                f"{self.model_cls} expect one data, but got {len(results)} datas",
            )
        if len(results) == 1:
            return results[0]
        raise NoMatchDataError(f"No match data for {self.model_cls}")

    async def all(self) -> List[Dict[str, Any]]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(*self.querys)),
        )
        return [result_one._asdict() for result_one in result.fetchall()]

    async def random_one(self) -> Optional[Dict[str, Any]]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(*self.querys)).order_by(func.random()),
        )
        if result_one := result.fetchone():
            return result_one._asdict()
        return None

    async def paginate(self, page: int, page_size: int) -> List[Dict[str, Any]]:
        if page < 1 or page_size < 1:
            raise PaginateArgError("page and page_size must be positive")
        self.options.limit = page_size
        self.options.offset = (page - 1) * page_size
        return await self.all()


class CoalesceQuerySet(QuerySetProtocol, Generic[Unpack[Ts]]):
    def __init__(
        self,
        *columns: Unpack[Ts],
        model_cls: Type[T_MODEL],
        options: QueryOptions,
    ) -> None:
        self.columns = columns
        self.model_cls = model_cls
        self.options = options

    async def first(self) -> Union[Unpack[Ts], None]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(*self.columns)),
        )
        if result_one := result.fetchone():
            return result_one[0]
        return None

    async def get(self) -> Union[Unpack[Ts], None]:
        results = await self.all()
        if len(results) > 1:
            raise MultipleDataError(
                f"{self.model_cls} expect one data, but got {len(results)} datas",
            )
        if len(results) == 1:
            return results[0]
        raise NoMatchDataError(f"No match data for {self.model_cls}")

    async def all(self) -> List[Union[Unpack[Ts], None]]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(func.coalesce(*self.columns))),
        )
        return [result_one[0] for result_one in result.fetchall()]

    async def random_one(self) -> Union[Unpack[Ts], None]:
        result = await self.model_cls.database.execute(
            self.options.as_select_option(select(*self.columns)).order_by(
                func.random(),
            ),
        )
        if result_one := result.fetchone():
            return result_one[0]
        return None

    async def paginate(
        self,
        page: int,
        page_size: int,
    ) -> List[Union[Unpack[Ts], None]]:
        if page < 1 or page_size < 1:
            raise PaginateArgError("page and page_size must be positive")
        self.options.limit = page_size
        self.options.offset = (page - 1) * page_size
        return await self.all()
