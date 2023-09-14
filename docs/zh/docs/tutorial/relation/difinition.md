# 关系模型定义

## 定义模型间关系

`Cherry` 支持关系型数据库的一对一、一对多以及多对多关系，只需简单的配置即可。

### 一对一

要声明一对一关系，只需使用 `cherry.ForeignKey` 注解包裹对应的模型即可，在对应的模型上则使用 `cherry.ReverseRelation` 来声明反向关系。

```python hl_lines="11 21"
--8<-- "./tutorial/relation/block1.py"
```

### 一对多

一对多和一对一关系类似，只需要把 `cherry.ReverseRelation[Model]` 改成 `cherry.ReverseRelation[List[Model]]`，注解为模型列表即可。

```python hl_lines="11 21"
--8<-- "./tutorial/relation/block2.py"
```

### 多对多

多对多关系关系则使用 `cherry.ManyToMany` 来注解。

```python hl_lines="11 21"
--8<-- "./tutorial/relation/block3.py"
```

### 关系字段配置

`ForeignKey`, `ReverseRelation`, `ManyToMany` 等注解只能在模型主键只有**一个**时使用，如果是复合主键或者想要使用其他字段做外键，则需要使用 `cherry.Relationship` 来声明。

另外，关于表关系的级联操作等，也需要在 `cherry.Relationship` 中定义。

`cherry.Relationship` 具有以下参数：

- foreign_key - 外键目标字段。在一对一或一对多关系的外键侧表的使用，指定使用目标表的哪个字段作为外键。
- foreign_key_extra - 一些传给 `sqlalchemy.ForeignKey` 的额外配置。
- reverse_related - 反向关系字段。在一对一或一对多关系中的反向关系中使用，设为 `True` 即可。
- many_to_many - 多对多外键字段。在多对多关系中使用，指定自身模型的哪个字段为多对多关系中的外键值。
- on_update - 相关模型更新时采取的措施，来自 `sqlalchemy.ForeignKey`。
- on_delete - 相关模型删除时采取的措施，来自 `sqlalchemy.ForeignKey`。
- related_field - 关联的字段。通常无需你自己配置，模型会自动查找。

`on_update` 和 `on_delete` 允许的值有：

- RESTRICT - 限制更新/删除。
- CASCADE - 级联更新/删除。
- SET NULL - 设为 NULL(None)，如果字段不允许为 None，则会抛出异常。
- SET DEFAULT - 设为默认值，如果字段没有默认值，则会抛出异常。
- NO ACTION - 不做任何行动，该报错就报错。

以下是两个例子。

#### 一对一、一对多

```python hl_lines="4 19"
--8<-- "./tutorial/relation/block4.py:8:30"
```

#### 多对多

```python hl_lines="5 21"
--8<-- "./tutorial/relation/block4.py:33:57"
```
