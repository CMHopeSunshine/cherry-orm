# 查询

`Cherry` 提供了非常丰富的查询方式以及两种查询style，能够满足大部分的查询需求。

## `get`

根据查询条件，获取指定模型数据，如不存在则抛出异常

=== "Pythonic style"

    ```python
    --8<-- "./tutorial/crud/query.py:23:23"
    ```

=== "Djange style"

    ```python
    --8<-- "./tutorial/crud/query.py:25:25"
    ```

## `get_or_none`

根据查询条件，获取指定模型数据，如不存在则返回 `None`

=== "Pythonic style"

    ```python
    --8<-- "./tutorial/crud/query.py:28:28"
    ```

=== "Djange style"

    ```python
    --8<-- "./tutorial/crud/query.py:30:30"
    ```

## `get_or_create`

根据查询条件，获取指定模型数据，如不存在则使用查询条件和 `default` 中的值来创建它。

返回值类型为 `Tuple[Model, bool]`，第一个值为模型实例，第二个值是 `bool` 类型，`True` 表示获取到了模型实例，`False` 表示创建了模型实例。

=== "Pythonic style"

    ```python
    --8<-- "./tutorial/crud/query.py:33:36"
    ```

=== "Djange style"

    ```python
    --8<-- "./tutorial/crud/query.py:38:41"
    ```

## `filter`

根据查询条件来进行进一步的复杂查询。

`filter` 实际上返回的是一个 `QuerySet` 对象，它可以继续做链式调用来进行更复杂的查询，最终通过调用 `first`, `all`, `get`, `random_one` 或 `paginate` 来返回结果。

=== "Pythonic style"

    ```python
    --8<-- "./tutorial/crud/query.py:44:48"
    ```

=== "Djange style"

    ```python
    --8<-- "./tutorial/crud/query.py:51:55"
    ```

### `first`

返回查询结果的第一个值，如无则返回 `None`

### `all`

返回查询结果的所有值

### `get`

返回查询结果的值，如果结果有多个，或者没有结果，均会抛出异常

### `random_one`

返回查询结果的随机一个值，如无则返回 `None`

### `paginate`

根据给定的页数和每页数量，返回查询结果的分页值列表

### `order_by`

根据给定的字段对查询结果进行排序

```python
--8<-- "./tutorial/crud/query.py:57:57"
```

### `limit`

根据给定的值对查询结果的数量进行限制

```python
--8<-- "./tutorial/crud/query.py:58:58"
```

### `offset`

根据给定的值对查询结果进行偏移

```python
--8<-- "./tutorial/crud/query.py:59:59"
```

### `values`

以元组的形式返回模型部分字段。

`values` 接受多个位置参数，即要获取的模型字段。

`values` 还有一个关键字参数 `flatten`，默认为 `False`，当设置为 `True` 时，位置参数必须有且仅有一个，返回结果元组会被展平。

```python
--8<-- "./tutorial/crud/query.py:61:69"
```

### `value_dict`

以字典的形式返回模型的部分字段。

`value_dict` 接受多个位置参数，即要获取的模型字段，若不传入，则为模型全部非关系字段。

```python
--8<-- "./tutorial/crud/query.py:71:74"
```

## `select`

`select` 是 `filter` 的无查询条件的版本，支持与 `filter` 一样的功能。

## `all`

它是 `Model.filter().all()` 的简写，返回该模型所有模型数据。

```python
--8<-- "./tutorial/crud/query.py:76:76"
```

## 完整代码

??? tip "本章完整示例代码"

    ```python
    --8<-- "./tutorial/crud/query.py"
    ```
