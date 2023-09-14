# 关系模型增删改查

## 读取

### `filter().prefetch_related`

通常的 `get`, `filter` 等查询函数，并不会同时返回相关联的模型，你可以通过在 `filter` 时添加 `prefetch_related` 选项，让其同时获取相关联的模型。

```python hl_lines="3 8"
--8<-- "./tutorial/relation/block2.py:59:67"
```

`prefetch_related` 接受若干个位置参数，用于指定要同时获取的字段。

### `select_related`

`select_related` 是模型类上的没有查询条件的 `filter().prefetch_related` 的简写，它的参数与 `prefetch_related` 相同。

### `fetch_related`

你也可以在模型实例上调用 `fetch_related`，来让该模型实例获取与它相关联的模型，它的参数与 `prefetch_related` 相同。

```python hl_lines="2"
--8<-- "./tutorial/relation/block2.py:69:71"
```

## 插入

### `insert`

```python hl_lines="2 4"
--8<-- "./tutorial/relation/block2.py:31:34"
```

!!! note "关系字段"
    对于有相关关系的模型，`insert` 和 `insert_many` 只会将自身和关系模型实例之间建立关系，而不会将关系模型一起插入到数据库中，也就是说，你必须先将关系模型插入到数据库中，然后再赋值给模型实例的关系字段上。正如该例子，你需要先将 `school` 插入到数据库中，再将其赋值给 `student` 的 `school` 字段上。

此外，`insert` 接受一个类型为 `bool` 的 `exclude_related` 参数，用于指定是否要与关系模型实例建立关系，默认为 `False`。

### `insert_with_related`


你可以使用模型实例的 `insert_with_related` 方法，将关系模型连同自身一起插入到数据库中：

```python hl_lines="8 11"
--8<-- "./tutorial/relation/block2.py:36:46"
```

这样就可以省去先插入关系模型的步骤了。

### `add`

该方法仅适用于 `ManyToMany` 多对多关系上，它接受一个模型实例，将该模型实例添加到自己的多对多字段值上。

如果提供的模型是非多对多关系字段模型，则会抛出异常。

```python hl_lines="7 8 10"
--8<-- "./tutorial/relation/block3.py:31:46"
```

## 删除

对于一对多和多对多关系模型，在模型定义时有级联相关配置。

### `remove`

对于多对多关系，可以调用 `remove` 来将模型实例从自己的字段上删除。

如果提供的模型是非多对多关系字段模型，则会抛出异常。

```python hl_lines="1"
--8<-- "./tutorial/relation/block3.py:48:52"
```

## 完整代码

??? tip "一对多完整示例代码"

    ```python
    --8<-- "./tutorial/relation/block2.py"
    ```

??? tip "多对多完整示例代码"

    ```python
    --8<-- "./tutorial/relation/block3.py"
    ```
