# Installation

!!! note "Python Version"

    `Cherry-ORM` only support Python 3.8+，Make sure your version of Python meets the requirements。

## Installation

### from PYPI

You can install `Cherry-ORM` using your favorite Python package manager, such as `pip`,`poetry`,`pdm` etc。

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
### from GIT

You can also install it from the source code to get the latest development version.

```shell
git clone https://github.com/CMHopeSunshine/cherry-orm
cd cherry-orm
pip install .
```

## Optional Dependency

Choose which dependencies to install based on your database backend.

### SQLite

```shell
pip install cherry-orm[sqlite]
# or
poetry add cherry-orm[sqlite]
# or
pdm add cherry-orm[sqlite]
```
`aiosqlite` will be installed for you to support asynchrony.

### MySQL

```shell
pip install cherry-orm[mysql]
# or
poetry add cherry-orm[mysql]
# or
pdm add cherry-orm[mysql]
```
`asyncmy` will be installed for you to support asynchrony.

### PostgreSQL

```shell
pip install cherry-orm[postgresql]
# or
poetry add cherry-orm[postgresql]
# or
pdm add cherry-orm[postgresql]
```
`asyncpg` will be installed for you to support asynchrony.

### Install manually

Of course, you can manually install the back-end dependencies you need, such as `pip install aiomysql`。
