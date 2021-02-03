from os import replace
from typing import List, Dict, Any, Callable
import os
import re
import json
import functools


ST_UNKNOWN  = "*"
ST_BOOL     = "bool"
ST_INT      = "integer"
ST_STR      = "string"
ST_FLOAT    = "float"
ST_URL      = "url"
ST_DATETIME = "datetime"

REGEXP_URL  = re.compile('^https?://.+$')
REGEXP_DATE = re.compile('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')



class TypeBase:
    @property
    def isLeaf(self) -> bool:
        return True

class NullType(TypeBase):
    def __repr__(self) -> str:
        return 'null'

class UniTypeHolder(TypeBase):
    def __init__(self, vtype: TypeBase) -> None:
        assert(type(vtype) != NullType)
        self._type = vtype
    @property
    def type(self) -> TypeBase:
        return self._type
    def replaceWithCommonObject(self, commonObject: 'CommonObjectType'):
        self._type = commonObject
    @property
    def isLeaf(self) -> bool:
        if self._type is None:
            return False
        return self._type.isLeaf

class Nullable(UniTypeHolder):
    def __repr__(self) -> str:
        return str(self._type) + '?'

class ValueType(TypeBase):
    def __init__(self, typename: str) -> None:
        assert(type(typename) == str)
        self.__typename = typename
    def __eq__(self, other):
        return type(other) == ValueType and self.__typename == other.__typename
    def __repr__(self) -> str:
        return '"' + self.__typename + '"'
    @property
    def typename(self):
        return self.__typename

class ArrayType(UniTypeHolder):
    def __repr__(self) -> str:
        return '[' + str(self._type) + ']' if self._type is not None else '[]'

class ObjectType(TypeBase):
    def __init__(self, props) -> None:
        assert(type(props) == dict)
        self.__props = props
    @property
    def isLeaf(self) -> bool:
        return False
    @property
    def isPlain(self):
        return all(map(lambda e: e.isLeaf, self.__props.values()))
    def get(self, v):
        return self.__props.get(v, None)
    def keys(self):
        return self.__props.keys()
    def items(self):
        return self.__props.items()
    def __repr__(self) -> str:
        return '{' + ','.join(['"%s":%s' % (k,str(v)) for (k,v) in self.__props.items()]) + '}'
    @property
    def numOfKeys(self):
        return len(list(self.keys()))
    def hasSameKeysOf(self, other) -> bool:
        assert(type(other) == ObjectType)
        return set(self.keys()) == set(other.keys())
    def containsAllKeysOf(self, other) -> bool:
        assert(type(other) == ObjectType)
        return set(self.keys()).issuperset(set(other.keys()))
    def replaceWithCommonObject(self, key, commonObject: 'CommonObjectType'):
        self.__props[key] = commonObject

class CommonObjectType(TypeBase):
    def __init__(self, typename, object: ObjectType) -> None:
        assert(type(object) == ObjectType)
        self.__typename = typename
        self.__object = object
    def __repr__(self) -> str:
        return '"$' + self.__typename + '"'
    @property
    def typename(self):
        return self.__typename
    @property
    def object(self):
        return self.__object


def __guessTypeForValue(v):
    assert(type(v) != dict and type(v) != list)
    if type(v) == type(None): return NullType()

    typemap = {
        bool: ST_BOOL,
        int:  ST_INT,
        str:  ST_STR,
        float: ST_FLOAT
    }

    vtype = typemap.get(type(v), NullType())
    if type(vtype) == NullType:
        return NullType()

    if vtype == ST_STR:
        if v.find('http://') == 0 or v.find('https://') == 0:
            if v.find('{') == -1: # FIXME ???
                return ValueType(ST_URL)
        if REGEXP_DATE.match(v):
            return ValueType(ST_DATETIME)

    return ValueType(vtype)

def __guessTypeForArray(json) -> ArrayType:
    assert(type(json) == list)
    def aggregateArrayOfObjectType(array):
        keys = functools.reduce(lambda a, e: a.union(set(e.keys())), array, set())
        if len(keys) == 0:
            return ArrayType(None)

        merged = {}
        for obj in array:
            for key in keys:
                value = obj.get(key)
                if type(value) == ObjectType:
                    merged[key] = value
                #elif type(value) == ArrayType:
                #    merged[key] = aggregateArrayOfObjectType(value)
                elif key in merged:
                    if type(merged[key]) == NullType and type(value) == NullType:
                        pass
                    elif type(merged[key]) == ObjectType and type(value) == NullType:
                        merged[key] = Nullable(merged[key])
                    elif type(merged[key]) == NullType and type(value) == ObjectType:
                        merged[key] = Nullable(value)
                    elif type(merged[key]) == type(value) and type(value) == ValueType and merged[key] == value:
                        pass
                    else:
                        pass
                        #merged[key] = merged[key].union(value)
                else:
                    merged[key] = value
        return ArrayType(ObjectType(merged))

    if all([type(i) == dict for i in json]):
        arr = [__guessTypeForDict(i) for i in json]
        return aggregateArrayOfObjectType(arr)

    types = functools.reduce(lambda a, e: a.union(set([type(e)])), json, set())
    if len(types) == 1:
        return ArrayType(__guessTypeForValue(json[0]))

    assert(False)

def __guessTypeForDict(json) -> ObjectType:
    assert(type(json) == dict)
    return ObjectType({k:guessType(v) for (k,v) in json.items()})

def guessType(value) -> TypeBase:
    if type(value) == dict:
        return __guessTypeForDict(value)
    elif type(value) == list:
        return __guessTypeForArray(value)
    else:
        return __guessTypeForValue(value)

def collectNonNestedObjects(obj: TypeBase, path: str = '', collected_map: Dict[str, TypeBase] = dict()) -> Dict[str, TypeBase]:
    if obj.isLeaf:
        return collected_map
    if obj.isPlain:
        collected_map[path] = obj
        return collected_map

    assert(type(obj) == ObjectType)
    for key, value in obj.items():
        if type(value) == Nullable and type(value.type) == ObjectType:
            collectNonNestedObjects(value.type, path + '/' + key + '?', collected_map)
        elif type(value) == ObjectType:
            collectNonNestedObjects(value, path + '/' + key, collected_map)
        elif type(value) == ArrayType and type(value.type) == ObjectType:
            collectNonNestedObjects(value.type, path + '/' + key + '/0', collected_map)
    return collected_map

def exactMatch(a: ObjectType, b: ObjectType):
    return a.numOfKeys > 0 and a.isPlain and a.hasSameKeysOf(b)

def similarMatch(a: ObjectType, b: ObjectType):
    return a.numOfKeys > 0 and a.isPlain and a.containsAllKeysOf(b) and a.numOfKeys > 3

def bothMatch(a: ObjectType, b: ObjectType):
    return exactMatch(a, b) or similarMatch(a, b)

class Endpoint:
    def __init__(self, request: Dict, response: TypeBase, rawResponse: str) -> None:
        self.__request = request
        self.__response = response
        self.__rawResponse = rawResponse

    @property
    def request(self):
        return self.__request
    @property
    def response(self):
        return self.__response
    @property
    def rawResponse(self):
        return self.__rawResponse

    def replaceWithCommonObject(self, commonObject: CommonObjectType):
        cond = lambda v: bothMatch(commonObject.object, v)

        def visitObject(obj: TypeBase):
            if obj.isLeaf:
                return 0

            if type(obj) != ObjectType:
                return 0

            assert(type(obj) == ObjectType)
            replaceCount = 0
            for key, value in obj.items():
                #print('   ', value)
                if type(value) == ObjectType:
                    if cond(value):
                        replaceCount += 1
                        obj.replaceWithCommonObject(key, commonObject)
                    elif not value.isPlain:
                        replaceCount += visitObject(value)
                elif type(value) == ArrayType and type(value.type) == ObjectType:
                    if cond(value.type):
                        replaceCount += 1
                        value.replaceWithCommonObject(commonObject)
                    else:
                        replaceCount += visitObject(value.type)
                elif type(value) == Nullable and type(value.type) == ObjectType:
                    if cond(value.type):
                        replaceCount += 1
                        value.replaceWithCommonObject(commonObject)
                    else:
                        replaceCount += visitObject(value.type)
            return replaceCount

        #print('>>>>', self.__request['name'])
        replaceCount = 0
        if type(self.__response) == ObjectType and cond(self.__response):
            replaceCount = 1
            self.__response = commonObject
        else:
            replaceCount = visitObject(self.__response)
        return replaceCount

    def nonNextedResponseObjects(self) -> Dict[str, TypeBase]:
        def resolveTypename(path):
            n = [e for e in path.split('/') if not e.isdigit()][-1]
            if len(n) == 0:
                return self.__request['name'] + 'Response'
            return n if n[-1] != '?' else n[:-1]

        if self.__response is None:
            return None
        if type(self.__response) == ArrayType:
            return None
        d = collectNonNestedObjects(self.__response, '', dict())
        return {resolveTypename(k):v for (k,v) in d.items() if len(v.keys()) > 0}

    def __repr__(self) -> str:
        return '%s = %s' % (self.__request['name'], self.__response)

class API:
    def __init__(self, endpoints: List[Endpoint] = []) -> None:
        self.__endpoints = endpoints
        self.__commonObjects = []

    def endpoints(self) -> List[Endpoint]:
        return self.__endpoints

    def commonObjects(self) -> List[CommonObjectType]:
        return self.__commonObjects

    def __resolveTypename(self, typenameCanditates: List[str]):
        exists = lambda name: any(filter(lambda e: e.typename == name, self.__commonObjects))
        def rename(name):
            for i in range(26):
                newTypename = name + chr(ord('A') + i) + 'xx'
                if not exists(newTypename):
                    return newTypename
            assert('Temporary typename exhausted' and False)

        filteredTypenameCanditates = sorted([e for e in typenameCanditates if len(e) > 0], key=functools.cmp_to_key(lambda a,b:len(a) - len(b)))
        typename = filteredTypenameCanditates[0]
        cappedTypename = typename[0].upper() + typename[1:]
        return rename(cappedTypename) if exists(cappedTypename) else cappedTypename

    def findAndRegisterSimilarObjects(self):
        def findSimilarObject(objects: List[ObjectType], matchFunction: Callable[[ObjectType, ObjectType], bool]) -> CommonObjectType:
            for (_, obj) in objects:
                if any(filter(lambda e: matchFunction(e.object, obj), self.__commonObjects)): continue
                typenameCanditates = [n for (n,o) in objects if matchFunction(obj, o)]
                if len(typenameCanditates) >= 2:
                    return CommonObjectType(self.__resolveTypename(typenameCanditates), obj)
            return None

        for i in range(100000):
            #nonNestedObjects = functools.reduce(lambda a, e: a + list(e.nonNextedResponseObjects().items()), self.__endpoints, [])
            nonNestedObjects = []
            for e in self.__endpoints:
                objs = e.nonNextedResponseObjects()
                if objs is None:
                    continue
                nonNestedObjects += objs.items()

            sot = findSimilarObject(nonNestedObjects, exactMatch) or findSimilarObject(nonNestedObjects, similarMatch)
            if sot is None:
                break
            self.__commonObjects.append(sot)
            for e in self.__endpoints:
                e.replaceWithCommonObject(sot)

    @staticmethod
    def initWithDir(dir: str, lang: str):
        endpoints = []
        #for d in ['get-message.json', 'get-messages.json']: #os.listdir(os.path.join(dir, 'api')):
        path = os.path.join(dir, 'api', lang)
        for d in os.listdir(path):
            with open(os.path.join(path, d)) as req:
                req_json = json.load(req)
                res_text = None
                res_json = None
                try:
                    with open(os.path.join(dir, 'response', d)) as res:
                        res_text = ''.join(res.readlines())
                        res_json = json.loads(res_text)
                except (OSError, IOError) as e:
                    pass # when reponse file doesn't exist

                endpoint = Endpoint(req_json, guessType(res_json), res_text)
                endpoints.append(endpoint)

        return API(endpoints)
