# 聚合查询

`Cherry` 支持部分聚合查询。

## `count`

获取查询结果的数量。

```python
--8<-- "./tutorial/crud/aggregation.py:27:27"
```

## `avg`

获取查询结果指定字段的平均值。

```python
--8<-- "./tutorial/crud/aggregation.py:28:28"
```

## `min`

获取查询结果指定字段的最小值。

```python
--8<-- "./tutorial/crud/aggregation.py:29:29"
```

## `max`

获取查询结果指定字段的最大值。

```python
--8<-- "./tutorial/crud/aggregation.py:30:30"
```

## `sum`

获取查询结果指定字段的总和。

```python
--8<-- "./tutorial/crud/aggregation.py:31:31"
```

## `coalesce`

获取查询结果指定字段的合并取值，返回字段列表中的第一个非空值，如都为空，则返回 `None`。

```python
--8<-- "./tutorial/crud/aggregation.py:32:37"
```

## 完整代码

??? tip "本章完整示例代码"

    ```python
    --8<-- "./tutorial/crud/aggregation.py"
    ```
