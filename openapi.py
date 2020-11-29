from typing import Optional, List, Dict

## Partial implementation of OpenAPI
# - OpenAPI Object
#     - openapi
#     - info
#     - paths
#     - components
# - Info Object
#     - title
#     - version
# - Paths Object
#     - get
#     - put
#     - post
#     - delete
#     - patch
# - Path Item Object
# - Components Object
#     - schemas
#     - responses
# - Reference Object
#     - $ref
# - Schema Object
#     - title
#     - type
#     - required
#     - nullable
#     - items
#     - enum
#     - properties
#     - format
#     - default
#     - description
# - Media Type Object
# - Data Types

class classproperty(property):
    def __get__(self, _, owner):
        return classmethod(self.fget).__get__(None, owner)()

class staticproperty(property):
    def __get__(self, _, owner):
        return staticmethod(self.fget).__get__(None, owner)()

class OperationVerb:
    def __init__(self, value) -> None:
        self.__value = value
    def __str__(self) -> str:
        return self.__value

    @staticproperty
    def get() : return OperationVerb('get')
    @staticproperty
    def put()  : return OperationVerb('put')
    @staticproperty
    def post(): return OperationVerb('post')
    @staticproperty
    def delete() : return OperationVerb('delete')
    @staticproperty
    def options() : return OperationVerb('options')
    @staticproperty
    def head(): return OperationVerb('head')
    @staticproperty
    def patch(): return OperationVerb('patch')
    @staticproperty
    def trace(): return OperationVerb('trace')


class DataType:
    def __init__(self, value) -> None:
        self.__value = value
    def __str__(self) -> str:
        return self.__value

    @staticproperty
    def object() : return DataType('object')
    @staticproperty
    def array()  : return DataType('array')
    @staticproperty
    def integer(): return DataType('integer')
    @staticproperty
    def number() : return DataType('number')
    @staticproperty
    def string() : return DataType('string')
    @staticproperty
    def boolean(): return DataType('boolean')


class DataFormat:
    def __init__(self, value) -> None:
        self.__value = value
    def __str__(self) -> str:
        return self.__value

    @staticproperty
    def int32()    : return DataFormat('int32')
    @staticproperty
    def int64()    : return DataFormat('int64')
    @staticproperty
    def float()    : return DataFormat('float')
    @staticproperty
    def double()   : return DataFormat('double')
    @staticproperty
    def byte()     : return DataFormat('byte')
    @staticproperty
    def binary()   : return DataFormat('binary')
    @staticproperty
    def date()     : return DataFormat('date')
    @staticproperty
    def datetime() : return DataFormat('datetime')
    @staticproperty
    def password() : return DataFormat('password')
    @staticproperty
    def email()    : return DataFormat('email')
    @staticproperty
    def url()      : return DataFormat('url')


class PrimitiveDataType:
    def __init__(self, type: DataType = DataType.object, format: Optional[DataFormat] = None):
        self.__type = type
        self.__format = format

    def toJson(self):
        obj = {
            'type': str(self.__type),
        }
        if self.__format is not None:
            obj['format'] = str(self.__format)
        return obj

    @staticproperty
    def integer() : return PrimitiveDataType(DataType.integer)
    @staticproperty
    def number()  : return PrimitiveDataType(DataType.number)
    @staticproperty
    def int32()   : return PrimitiveDataType(DataType.integer, DataFormat.int32)
    @staticproperty
    def int64()   : return PrimitiveDataType(DataType.integer, DataFormat.int64)
    @staticproperty
    def float()   : return PrimitiveDataType(DataType.number , DataFormat.float)
    @staticproperty
    def double()  : return PrimitiveDataType(DataType.number , DataFormat.double)
    @staticproperty
    def string()  : return PrimitiveDataType(DataType.string)
    @staticproperty
    def byte()    : return PrimitiveDataType(DataType.string , DataFormat.byte)
    @staticproperty
    def binary()  : return PrimitiveDataType(DataType.string , DataFormat.binary)
    @staticproperty
    def boolean() : return PrimitiveDataType(DataType.boolean)
    @staticproperty
    def date()    : return PrimitiveDataType(DataType.string , DataFormat.date)
    @staticproperty
    def datetime(): return PrimitiveDataType(DataType.string , DataFormat.datetime)
    @staticproperty
    def password(): return PrimitiveDataType(DataType.string , DataFormat.password)
    @staticproperty
    def email()   : return PrimitiveDataType(DataType.string , DataFormat.email)
    @staticproperty
    def url()     : return PrimitiveDataType(DataType.string , DataFormat.url)

class SchemaObject(PrimitiveDataType):
    def __init__(self, title: Optional[str] = None, properties: Dict[str, PrimitiveDataType] = None, required: List[str] = [], nullable: bool = False, items = [], default = None, description: str = ''):
        super().__init__()
        self.__title = title
        self.__properties = properties
        self.__required = required
        self.__nullable = nullable
        self.__items = items
        self.__default = default
        self.__description = description

    def toJson(self):
        obj = super().toJson()
        if self.__title is not None:
            obj['title'] = self.__title
        if self.__properties is not None:
            obj['properties'] = {k: v.toJson() for k, v in self.__properties.items() if v is not None} # FIXME None
        if len(self.__required) > 0:
            obj['required'] = self.__required
        return obj

    @staticmethod
    def newObject(title, properties):
        return SchemaObject(title, properties)

class ComponentsObject:
    def __init__(self, schemas: Dict[str, SchemaObject] = {}) -> None:
        self.__schemas = schemas
        #self.__responses = responses

    def toJson(self):
        obj = {
            'schemas': {k: v.toJson() for k, v in self.__schemas.items()}
        }
        return obj

class InfoObject:
    def __init__(self, title: str, version: str, description: Optional[str] = None, termsOfService: Optional[str] = None) -> None:
        self.__title = title
        self.__version = version
        self.__description = description
        self.__termsOfService = termsOfService

    def toJson(self):
        obj = {
            'title': self.__title,
            'version': self.__version
        }
        if self.__description is not None:
            obj['description'] = self.__description
        if self.__termsOfService is not None:
            obj['termsOfService'] = self.__termsOfService
        return obj

class PathsObject:
    def __init__(self, paths: Dict[str, 'PathItemObject'] = dict()) -> None:
        self.__paths = paths

class PathItemObject:
    def __init__(self, summary: Optional[str] = None, description: Optional[str] = None, oprations: Dict[OperationVerb, 'OperationObject'] = dict()) -> None:
        self.__summary = summary
        self.__description = description
        self.__oprations = oprations

class OperationObject:
    def __init__(self, summary: Optional[str] = None, description: Optional[str] = None) -> None:
        self.__summary = summary
        self.__description = description


class OpenAPI:
    def __init__(self, openApiVersion = "3.0.3", info: InfoObject = InfoObject('', ''), components: ComponentsObject = ComponentsObject() ) -> None:
        self.__openapi = openApiVersion
        self.__info = info
        self.__components = components

    def toJson(self):
        obj = {
            'openapi': self.__openapi,
            'info': self.__info.toJson(),
            'components': self.__components.toJson()
        }
        return obj
