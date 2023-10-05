# 模型定义

## 定义模型

### 模型类

你可以和 `Pydantic` 一样轻松地定义一个数据库模型，只需继承 `cherry.Model` 类即可。

以下是一个最简单的模型。

```python hl_lines="6"
--8<-- "./tutorial/definition/block1.py"
```

### 模型字段

可以用 `cherry.Field` 对模型的字段进行详细设置，就像 `pydantic.Field` 一样。

```python hl_lines="2-5"
--8<-- "./tutorial/definition/block2.py:4:10"
```

`cherry.Field` 支持 `pydantic.Field` 的所有配置，并增添了以下配置：

- primary_key - 主键
- autoincrement - 数据库自增
- index - 索引
- unique - 唯一约束
- nullable - 是否允许为空

同时它们还有一些简便写法，通过 `Annotated` 来实现：

=== "Field"

    ```python hl_lines="2-4"
    --8<-- "./tutorial/definition/block2.py:4:10"
    ```

=== "Annotated"

    ```python hl_lines="2-4"
    --8<-- "./tutorial/definition/block3.py:4:10"
    ```

对于数据库自增整型主键，你可以采用以下写法：

=== "Field"

    ```python hl_lines="8"
    --8<-- "./tutorial/definition/block4.py"
    ```

=== "Annotated"

    ```python hl_lines="7"
    --8<-- "./tutorial/definition/block5.py"
    ```

## 数据库绑定

在定义好 `Model` 之后，你尚未能够使用它。你需要创建一个 `cherry.Database` 对象，它负责与数据库进行连接交互，你需要传入一个**数据库连接字符串**，并且必须添加一个**支持异步**的后端，例如:

- `sqlite+aiosqlite:///test.db`
- `mysql+asyncmy://root:123456@localhost:3306/test`
- `postgresql+asyncpg://root:123456@localhost:5432/test`

```python
--8<-- "./tutorial/definition/block6.py:0:3"
```

然后通过模型的 `Meta` 类，将数据库对象绑定到模型上：

```python hl_lines="8"
--8<-- "./tutorial/definition/block6.py:4:13"
```

在 `Meta` 类中，你还可以定义以下配置：

- database - `cherry.Database` 对象，默认无。
- tablename - 模型在数据库中的表名。默认使用模型的类名作为表名，例如本处的 `User`。
- abstract - 是否为抽象模型。抽象模型即只用于继承，不作为数据库中的表，默认为 `False`。
- constraints - 更多 `sqlalchemy` 的表约束，类型为 `List[sqlalchemy.ColumnCollectionConstraint]`。
- indexes - 组合索引，类型为 `List[cherry.CompositeIndex]`。


## 模型初始化

在绑定数据库对象后，你还需要在你的入口文件中调用 `Database.init` 方法，对模型以及数据库进行初始化才能使用。

```python hl_lines="2"
--8<-- "./tutorial/definition/block6.py:16:23"
```
