#!/usr/bin/env python

from typing import Optional, List, Dict, Tuple
from os import pread
import sys
import json
import re
import os
import copy
import itertools
from collections import OrderedDict
import openapi
import ir

def toPrimitiveDataType(v: ir.TypeBase) -> openapi.PrimitiveDataType:
    if type(v) == ir.ValueType:
        m = {
            'bool': openapi.PrimitiveDataType.boolean,
            'integer': openapi.PrimitiveDataType.integer,
            'string': openapi.PrimitiveDataType.string,
            'url': openapi.PrimitiveDataType.url,
            'datetime': openapi.PrimitiveDataType.datetime,
            # TODO: add
        }
        return m.get(v.typename)
    elif type(v) == ir.NullType:
        return openapi.PrimitiveDataType.string # FIXME
    print(v)
    assert(False)

def toSchemaObject(cobj: ir.CommonObjectType) -> openapi.SchemaObject:
    props = {k:toPrimitiveDataType(v) for (k,v) in cobj.object.items()}
    sobj = openapi.SchemaObject(properties=props)
    return sobj

def toPath(url: str) -> str:
    def toTemplate(c: str) -> str:
        return '{' + c[1:] + '}' if len(c) > 0 and c[0] == ':' else c

    l = len('https://typetalk.com/api') #### FIXME
    path = url[l:]
    comp = [toTemplate(c) for c in path.split('/')]
    return '/'.join(comp)

def toOperationObjectTuple(endpoint: ir.Endpoint) -> Tuple[str, openapi.OperationVerb, openapi.OperationObject]:
    req = endpoint.request
    method = openapi.OperationVerb.fromStr(req['method'].lower())
    summary = req['name'] + ': ' + req['summary']
    description=req['description']
    op = openapi.OperationObject(summary, description)
    path = toPath(req['url'])
    return (path, method, op)

def toPathsDict(endpoints: List[Tuple[str, openapi.OperationVerb, openapi.OperationObject]]) -> Dict[str, openapi.PathItemObject]:
    f = lambda m: re.sub('/v[0-9]+', '', m[0])
    dic = OrderedDict()
    for (_, es) in itertools.groupby(sorted(endpoints, key=f), key=f):
        esl = list(es)
        path = esl[0][0]
        ops = {e[1]:e[2] for e in esl}
        dic[path] = openapi.PathItemObject(oprations=ops)
    return dic

class OpenApiConverter:
    def convert(self, title: str, version: str, api: ir.API) -> openapi.OpenAPI:
        schemaObjects = {o.typename:toSchemaObject(o) for o in api.commonObjects()}
        endpoints = [toOperationObjectTuple(e) for e in api.endpoints()]

        info = openapi.InfoObject(title, version)
        comps = openapi.ComponentsObject(schemaObjects)
        paths = openapi.PathsObject(toPathsDict(endpoints))
        oa = openapi.OpenAPI(info=info, paths=paths, components=comps)
        return oa


def main():
    appname = 'typetalk'
    api = ir.API.initWithDir(appname)
    api.findAndRegisterSimilarObjects()
    converter = OpenApiConverter()
    oa = converter.convert(appname[0].upper() + appname[1:], '1.0.0-20191003', api)
    print(json.dumps(oa.toJson()))

if __name__ == '__main__':
    main()
    
