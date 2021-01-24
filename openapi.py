from collections import OrderedDict
from typing import Any, Optional, List, Dict, Set, Union

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
    def __hash__(self):
        return hash(self.__value)
    def __eq__(self, other):
        return self.__value == other.__value
    def toJson(self):
        return self.__value

    @staticproperty
    def allItems():
        return [
           OperationVerb.get, 
           OperationVerb.put, 
           OperationVerb.post, 
           OperationVerb.delete, 
           OperationVerb.options, 
           OperationVerb.head, 
           OperationVerb.patch, 
           OperationVerb.trace, 
        ]

    @classmethod
    def fromStr(cls, string):
        m = OperationVerb.allItems
        z = list(filter(lambda e: e.__value == string, m))
        return z[0]

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

class ParameterLocation:
    def __init__(self, value) -> None:
        self.__value = value
    def __str__(self) -> str:
        return self.__value
    def __hash__(self):
        return hash(self.__value)
    def __eq__(self, other):
        return self.__value == other.__value
    def toJson(self):
        return self.__value

    @staticproperty
    def allItems():
        return [
           ParameterLocation.query, 
           ParameterLocation.header, 
           ParameterLocation.path, 
           ParameterLocation.cookie, 
        ]

    @classmethod
    def fromStr(cls, string):
        m = OperationVerb.allItems
        z = list(filter(lambda e: e.__value == string, m))
        return z[0]

    @staticproperty
    def query() : return ParameterLocation('query')
    @staticproperty
    def header()  : return ParameterLocation('header')
    @staticproperty
    def path(): return ParameterLocation('path')
    @staticproperty
    def cookie() : return ParameterLocation('cookie')

class DataType:
    def __init__(self, value) -> None:
        self.__value = value
    def __str__(self) -> str:
        return self.__value
    def toJson(self):
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
    def toJson(self):
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


def getAllParents(obj: object):
    r = set({})
    def __getAllParents(t: type):
        if t == object:
            return 
        r.add(t)
        for e in t.__bases__:
            __getAllParents(e)
    __getAllParents(type(obj))    
    return r

def newDictFrom(obj: object):
    '''collects all pairs of key and values of private members whose value isn't None or function from the given object'''
    def getKeyValuePairs(obj: object):
        privateMemberPrefixes = ['_' + e.__name__ + '__' for e in getAllParents(obj)]
        pairs = []
        for e in obj.__dir__():
            value = obj.__getattribute__(e)
            if value is None or callable(value): continue
            s = [x for x in privateMemberPrefixes if e.find(x) == 0]
            if len(s) == 0: continue
            prefix = s[0]
            key = e[len(prefix):]
            pairs.append((key, value))
        return pairs

    pairs = getKeyValuePairs(obj)
    conv = lambda v: v if type(v) == str or type(v) == bool or type(v) == int else ({str(k):conv(x) for k, x in v.items() if x is not None} if type(v) == dict or type(v) == OrderedDict else ([conv(x) for x in v] if type(v) == list else v.toJson()))
    q = {k:conv(v) for (k,v) in pairs}
    return q


class JsonConvertible:
    def toJson(self):
        return newDictFrom(self)

class PrimitiveDataType:
    def __init__(self, type: DataType = DataType.object, format: Optional[DataFormat] = None):
        self.type = type
        self.format = format

    def toSchemaObject(self) -> 'SchemaObject':
        return SchemaObject.initWithPrimitive(self)
        
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

class SchemaObject(JsonConvertible):
    def __init__(self, title: Optional[str] = None, properties: Dict[str, Union['SchemaObject', 'ReferenceObject']] = None, required: Optional[List[str]] = None, nullable: Optional[bool] = None, items: Optional[Union['SchemaObject', 'ReferenceObject']] = None, default = None, description: Optional[str] = None, type: DataType = DataType.object, format: Optional[DataFormat] = None):
        self.__type = type
        self.__format = format
        self.__title = title
        self.__properties = properties
        self.__required = required
        self.__nullable = nullable
        self.__items = items
        self.__default = default
        self.__description = description

    # TODO: delete this method for immutability
    def setNullable(self, n: bool):
        self.__nullable = n

    @classmethod
    def initWithPrimitive(cls, primiteveType: PrimitiveDataType, title: Optional[str] = None, nullable: Optional[bool] = None, default = None, description: Optional[str] = None):
        obj = SchemaObject(title=title, nullable=nullable, default=default, description=description, type=primiteveType.type, format=primiteveType.format)
        return obj

    @staticmethod
    def newObject(title, properties):
        return SchemaObject(title, properties)

class ComponentsObject(JsonConvertible):
    def __init__(self, schemas: Dict[str, Union[SchemaObject, 'ReferenceObject']] = {}) -> None:
        self.__schemas = schemas
        #self.__responses = responses

class InfoObject(JsonConvertible):
    def __init__(self, title: str, version: str, description: Optional[str] = None, termsOfService: Optional[str] = None) -> None:
        self.__title = title
        self.__version = version
        self.__description = description
        self.__termsOfService = termsOfService


class ContactObject(JsonConvertible):
    def __init__(self, name: Optional[str] = None, url: Optional[str] = None, email: Optional[str] = None) -> None:
        self.__name = name
        self.__url = url
        self.__email = email

class LicenceObject(JsonConvertible):
    def __init__(self, name: str, url: Optional[str] = None) -> None:
        self.__name = name
        self.__url = url

class PathsObject(JsonConvertible):
    def __init__(self, paths: Dict[str, 'PathItemObject'] = dict()) -> None:
        self.__paths = paths
    def toJson(self):
        dic = super().toJson()
        return dic['paths']

class PathItemObject(JsonConvertible):
    def __init__(self, summary: Optional[str] = None, description: Optional[str] = None, oprations: Dict[OperationVerb, 'OperationObject'] = dict()) -> None:
        self.__summary = summary
        self.__description = description
        self.__oprations = oprations
    def toJson(self):
        dic = super().toJson()
        z = dic.pop('oprations')
        for i in OperationVerb.allItems:
            if not i in self.__oprations: continue
            dic[str(i)] = self.__oprations[i].toJson()
        return dic

class OperationObject(JsonConvertible):
    def __init__(self, responses: 'ResponsesObject', summary: Optional[str] = None, description: Optional[str] = None, parameters: Optional[List['ParameterObject']] = None, requestBody: Optional['RequestBodyObject'] = None) -> None:
        self.__summary = summary
        self.__description = description
        self.__parameters = parameters
        self.__requestBody = requestBody

class ParameterObject(JsonConvertible):
    def __init__(self, name: str, locatedIn: ParameterLocation, required: Optional[bool] = None, description: Optional[str] = None) -> None:
        assert((locatedIn == ParameterLocation.path and required is not None) or locatedIn != ParameterLocation.path)
        self.__name = name
        self.__in = locatedIn
        self.__required = required
        self.__description = description

class RequestBodyObject(JsonConvertible):
    def __init__(self, content: Dict[str, 'MediaTypeObject'], description: Optional[str] = None, required: Optional[bool] = None):
        self.__content = content
    def toJson(self):
        dic = super().toJson()
        z = dic.pop('content')
        for k, v in self.__content.items(): # FIXME sort order
            dic[k] = v.toJson()
        return dic

class MediaTypeObject(JsonConvertible):
    def __init__(self, schema: Optional[Union[SchemaObject, 'ReferenceObject']], encoding: Optional[str] = None): ##, example = None, examples = None):
        self.__schema = schema

class ResponsesObject(JsonConvertible):
    def __init__(self, responses: Dict[str, 'ResponseObject']):
        self.__responses = responses
    def toJson(self):
        dic = super().toJson()
        z = dic.pop('responses')
        for k, v in self.__responses.items(): # FIXME sort order
            dic[k] = v
        return dic

class ResponseObject(JsonConvertible):
    def __init__(self, description: Optional[str] = None):
        self.__description = description

class ReferenceObject(JsonConvertible):
    def __init__(self, ref: str):
        self.__ref = ref
    def toJson(self):
        return { '$ref' : self.__ref }

class OpenAPI(JsonConvertible):
    def __init__(self, openApiVersion = "3.0.3", info: InfoObject = InfoObject('', ''), paths: PathsObject = PathsObject(), components: ComponentsObject = ComponentsObject() ) -> None:
        self.__openapi = openApiVersion
        self.__info = info
        self.__paths = paths
        self.__components = components

