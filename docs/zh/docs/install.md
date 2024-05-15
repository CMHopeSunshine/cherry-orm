# 安装

!!! note "Python 版本"

    `Cherry-ORM` 只支持 Python 3.9+，请确保你的 Python 版本符合要求。

## 安装

### PYPI 安装

可以使用你喜欢的 Python 包管理器来安装 `Cherry-ORM`，比如 `pip`、`poetry`、`pdm` 等。

#### PIP
```shell
pip install cherry-orm
```

#### Poetry
```shell
poetry add cherry-orm
```

#### PDM
```shell
pdm add cherry-orm
```
### GIT 安装

你也可以从源码安装，以获取最新的开发版本。

```shell
git clone https://github.com/CMHopeSunshine/cherry-orm
cd cherry-orm
pip install .
```

## 可选依赖

根据你的数据库后端来选择安装对应的依赖。

### SQLite

```shell
pip install cherry-orm[sqlite]
# 或者
poetry add cherry-orm[sqlite]
# 或者
pdm add cherry-orm[sqlite]
```
会为你安装 `aiosqlite` 来支持异步。

### MySQL

```shell
pip install cherry-orm[mysql]
# 或者
poetry add cherry-orm[mysql]
# 或者
pdm add cherry-orm[mysql]
```
会为你安装 `asyncmy` 来支持异步。

### PostgreSQL

```shell
pip install cherry-orm[postgresql]
# 或者
poetry add cherry-orm[postgresql]
# 或者
pdm add cherry-orm[postgresql]
```
会为你安装 `asyncpg` 来支持异步。

### 手动安装

当然，你可以手动安装你所需要的后端依赖，例如`pip install aiomysql`。
