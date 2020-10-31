#!/usr/bin/env python

import sys
import json
import re
import os
import functools
import copy
from collections import OrderedDict

ST_UNKNOWN  = "*"
ST_BOOL     = "bool"
ST_INT      = "integer"
ST_STR      = "string"
ST_FLOAT    = "float"
ST_URL      = "url"
ST_DATETIME = "datetime"


REGEXP_DATE = re.compile('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')


class ObjectTypeInfo:
    def __init__(self, attributeObject):
        self.attributeObject = attributeObject
        self.paths = set([])
        pass

    @property
    def __jsonPaths(self):
        return map(lambda e: e.split(':')[-1], self.paths)

    @property
    def __leafNames(self):
        return map(lambda e: e.split('/')[-1], self.__jsonPaths)

    @property
    def __directParentNames(self):
        return map(lambda e: e.split('/')[-2], filter(lambda e: len(e) > 1, self.__jsonPaths))

    def __names(self, genfunc):
        return list(set(filter(lambda e: e.isalnum() and not e.isdigit(), genfunc)))

    def types(self):
        single_or_list = lambda e: list(e)[0] if len(e) == 1 else (list(e) if len(e) > 1 else None)
        return {i : single_or_list(j) for i, j in self.attributeObject.items()}

    @property
    def typeNames(self):
        a = set(self.__names(self.__leafNames))
        if len(a) >= 1:
            t = set([self.getTypeName()])
            return list(map(lambda e: 'other candidate: ' + e, a - t))
        b = set(self.__names(self.__directParentNames))
        return list(map(lambda e: 'Type name `' + e + '` is generate from parent node name and probably have to be remove plural `s`.', b))

    def getTypeName(self):
        ns = self.__names(self.__leafNames)
        if len(ns) == 1 and ns[0] != '':
            return ns[0]
        elif len(ns) > 1:
            return ns[0]
        ns = self.__names(self.__directParentNames)
        return ns[0]

    def toJson(self):
        obj = self.types()
        obj['_meta'] = {
             'files': sorted(list(self.paths))
        }
        if len(self.typeNames) > 0:
            obj['_meta']['typename notes'] = self.typeNames
        return obj

def mergeIntoSingleObject(targetArray):
    keys = functools.reduce(lambda a, e: a.union(set(e.keys())), targetArray, set())
    merged = {}
    for obj in targetArray:
        for key in keys:
            value = obj.get(key, set([]))
            if type(value) == dict:
                merged[key] = value
            elif type(value) == list:
                merged[key] = mergeIntoSingleObject(value)
            elif key in merged:
                merged[key] = merged[key].union(value)
            else:
                merged[key] = value
    return [merged]

def guessTypenameForArray(json):
    arr = []
    for value in json:
        if type(value) == dict:
            arr.append(guessTypenameForDict(value))

    if all([type(i) == dict for i in arr]):
        return mergeIntoSingleObject(arr)

    assert(False)
    return arr # Unexpected return


def guessTypenameForDict(json):
    info = {}
    for key, value in json.items():
        if type(value) == dict:
            info[key] = guessTypenameForDict(value)
        elif type(value) == list:
            info[key] = guessTypenameForArray(value)
        else:
            info[key] = set([guessTypename(value)])
    return info

def guessTypename(v):
    if type(v) == type(None): return ST_UNKNOWN

    typemap = {
        bool: ST_BOOL,
        int:  ST_INT,
        str:  ST_STR,
        float: ST_FLOAT
    }

    typename = typemap.get(type(v), ST_UNKNOWN)
    if typename == ST_STR:
        if v.find('http://') == 0 or v.find('https://') == 0:
            if v.find('{') == -1: # FIXME ???
                return ST_URL
        if REGEXP_DATE.match(v):
            return ST_DATETIME

    return typename


# leaf object has no object itself.
def isLeafObject(obj):
    return all(map(lambda e: type(e) != list and type(e) != dict, obj.values()))

def collectLeafObjects(obj, path = '', collected_map = dict()):
    if isLeafObject(obj):
        collected_map[path] = guessTypenameForDict(obj)
        return collected_map

    ###collected_map[path] = guessTypenameForDict(obj)

    for key, value in obj.items():
        if type(value) == dict:
            collectLeafObjects(value, path + '/' + key, collected_map)
        elif type(value) == list:
            if len(value) > 0 and all([type(i) == dict for i in value]):
                collectLeafObjects(value[0], path + '/' + key + '/0', collected_map)
    return collected_map

def pathname(filepath, jsonpath):
    fp = filepath.split('/')[-1]
    fp = fp.split('.')[0]
    return fp + ':' + jsonpath

def findSameObject(file1, file2, registered):
    with open(file1) as f1, open(file2) as f2:
        obj1 = json.load(f1)
        obj2 = json.load(f2)
        m1 = collectLeafObjects(obj1)
        m2 = collectLeafObjects(obj2)

        for k1,v1 in m1.items():
            for k2,v2 in m2.items():
                #if v1 == v2:
                if set(v1.keys()) == set(v2.keys()):
                    assert(type(v1) == dict)
                    founds = list(filter(lambda e: e.attributeObject == v1, registered))
                    if len(founds):
                        assert(len(founds) == 1)
                        found = founds[0]
                        found.paths.add(pathname(file2, k2))
                    else:
                        ot = ObjectTypeInfo(v1)
                        ot.paths.add(pathname(file1, k1))
                        ot.paths.add(pathname(file2, k2))
                        registered.append(ot)
                    #print('\t\t' + pathname(file2, k2))

def findSameObjectForDir(dirpath):
    registered = list()
    for f1 in os.listdir(dirpath):
        #print(f1 + ' ' + '-' * 50)
        for f2 in os.listdir(dirpath):
            if f1 != f2: continue
            findSameObject(os.path.join(dirpath, f1), os.path.join(dirpath, f2), registered)
    return registered

reg = findSameObjectForDir('./typetalk/response/')
d = dict()
for i in reg:
    n = i.getTypeName()
    if len(n) > 0:
        n = n[0].upper() + n[1:]
    d[n] = i.toJson()

print(json.dumps(OrderedDict(sorted(d.items()))))

#findSameObject('./typetalk/response/add-message-to-talk.json', './typetalk/response/create-talk.json')