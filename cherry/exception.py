class CherryException(Exception):
    """Base exception for Cherry orm."""


class DatabaseNoBoundError(RuntimeError, CherryException):
    """Database is not bound."""


class ModelMissingError(ValueError, CherryException):
    """Model is missing."""


class ModelTypeError(TypeError, CherryException):
    """Model is not correct."""


class FieldTypeError(TypeError, CherryException):
    """Field type is not correct."""


class RelationSolveError(TypeError, CherryException):
    """Relation is not correct."""


class AbstractModelError(ValueError, CherryException):
    """The model is abstract."""


class PrimaryKeyMissingError(ValueError, CherryException):
    """Primary key is missing."""


class PrimaryKeyMultipleError(ValueError, CherryException):
    """Primary key is multiple."""


class ForeignKeyMissingError(ValueError, CherryException):
    """Foreign key is missing."""


class RelatedFieldMissingError(ValueError, CherryException):
    """Related field is missing."""


class MultipleDataError(ValueError, CherryException):
    """The query returned multiple datas when only one was expected."""


class NoMatchDataError(ValueError, CherryException):
    """The query returned no data when one was expected."""


class PaginateArgError(ValueError, CherryException):
    """The paginate args is not correct."""


class ClauseTypeError(TypeError, CherryException):
    """The clause type is not correct."""
