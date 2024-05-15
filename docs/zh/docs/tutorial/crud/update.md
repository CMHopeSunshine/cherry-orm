# 更新

## `save`

你可以在修改模型的字段后，调用模型的 `save` 来让修改结果更新到数据库中：

```python hl_lines="4"
--8<-- "./tutorial/crud/update.py:20:23"
```

???+ note "有则更新无则插入"
    `save` 也可以用于插入，当模型的主键已经存在数据库中时，则会更新，否则会插入该模型。

## `update`

或者使用 `update` 方法，传入要更新的值来更新：

```python
--8<-- "./tutorial/crud/update.py:25:25"
```

## `update_or_create`

使用 `update_or_create`，如果数据库中存在该模型，则更新，否则插入。

返回值类型为 `Tuple[Model, bool]`，第一个值为模型实例，第二个值是 `bool` 类型，`True` 表示更新了模型实例，`False` 表示创建了模型实例。

```python
--8<-- "./tutorial/crud/update.py:27:30"
```

它接受若干的查询条件，以及一个类型为 `Dict[str, Any]` 的 `defaults` 参数，用于指定要更新的字段及其值。

首先会根据查询条件查询指定数据，如果存在，则使用 `defaults` 字典里的数据来更新它，否则，会使用查询条件和 `defaults` 字典里的数据来创建一个新的模型并返回。

## `save_many`

使用模型类的 `save_many` 来同时更新多条数据：

```python
--8<-- "./tutorial/crud/update.py:32:39"
```

## 完整代码

??? tip "本章完整示例代码"

    ```python
    --8<-- "./tutorial/crud/update.py"
    ```
