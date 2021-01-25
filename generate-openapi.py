#!/usr/bin/env python

from typing import Optional, List, Dict, Tuple, Union
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

def toPrimitiveDataTypeFromStr(s: str) -> openapi.PrimitiveDataType:
    m = {
        'Number': openapi.PrimitiveDataType.integer,
        'String': openapi.PrimitiveDataType.string,
        # TODO: add
    }
    return m.get(s, openapi.PrimitiveDataType.string)

def toPrimitiveDataType(v: ir.TypeBase) -> Union[openapi.SchemaObject, openapi.ReferenceObject]:
    if type(v) == ir.ArrayType:
        return openapi.SchemaObject(type=openapi.DataType.array, items=toPrimitiveDataType(v.type))
    elif type(v) == ir.Nullable:
        s = toPrimitiveDataType(v.type)
        if type(s) is not openapi.ReferenceObject: ### FIXME
            s.setNullable(True)
        return s
    elif type(v) == ir.ValueType:
        m = {
            'bool': openapi.PrimitiveDataType.boolean,
            'integer': openapi.PrimitiveDataType.integer,
            'string': openapi.PrimitiveDataType.string,
            'url': openapi.PrimitiveDataType.url,
            'datetime': openapi.PrimitiveDataType.datetime,
            # TODO: add
        }
        return m.get(v.typename).toSchemaObject()
    elif type(v) == ir.NullType:
        return openapi.PrimitiveDataType.string.toSchemaObject() # FIXME: we assume an unguessable object as string

    return openapi.ReferenceObject('#/components/schemas/' + v.typename) # FIXME: ref path

def toSchemaObjectFromCommonObject(cobj: ir.CommonObjectType) -> openapi.SchemaObject:
    props = {k:toPrimitiveDataType(v) for (k,v) in cobj.object.items()}
    sobj = openapi.SchemaObject(properties=props)
    return sobj

def toRequestBodyParams(params: List[Dict[str, str]]) -> Dict[str, openapi.SchemaObject]:
    props = {}
    reqs = []
    for p in params:
        name = p['name']
        type = p['type']
        required = not p['optional']
        description = p['description']
        props[name] = openapi.SchemaObject.initWithPrimitive(toPrimitiveDataTypeFromStr(type), description=description)
        if required:
            reqs.append(name)
    return openapi.SchemaObject(properties=props, required=reqs)

def toParameterObject(params: Dict[str, str], location: openapi.ParameterLocation) -> openapi.ParameterObject:
    name = params['name']
    required = not params['optional']
    description = params['description']
    return openapi.ParameterObject(name, location, required, description)

def toParameterObjects(urlParams: List[Dict[str, str]], queryParams: List[Dict[str, str]]) -> Optional[List[openapi.ParameterObject]]:
    if len(urlParams) + len(queryParams) == 0:
        return None
    p = openapi.ParameterLocation.path
    q = openapi.ParameterLocation.query
    # TODO: formParams
    return [toParameterObject(e, p) for e in urlParams] + [toParameterObject(e, q) for e in queryParams]

def toRequestBodyObjects(formParams: List[Dict[str, str]]) -> Optional[openapi.RequestBodyObject]:
    if len(formParams) == 0:
        return None
    p = 'application/x-www-form-urlencoded'
    dic = {}
    dic[p] = openapi.MediaTypeObject(toRequestBodyParams(formParams))
    return openapi.RequestBodyObject(dic)

def toResponsesObject(response: ir.TypeBase) -> Optional[openapi.ResponsesObject]:
    if type(response) == ir.NullType:
        return None

    content = {}
    content['application/json'] = openapi.MediaTypeObject(toPrimitiveDataTypeFromStr('str').toSchemaObject())  # FIXME

    responses = {}
    responses['200'] = openapi.ResponseObject(content=content)
    return openapi.ResponsesObject(responses)

def toPath(url: str) -> str:
    def toTemplate(c: str) -> str:
        return '{' + c[1:] + '}' if len(c) > 0 and c[0] == ':' else c

    l = len('https://typetalk.com/api') #### FIXME should be considered for other services
    path = url[l:]
    comp = [toTemplate(c) for c in path.split('/')]
    return '/'.join(comp)

def toOperationObjectTuple(endpoint: ir.Endpoint) -> Tuple[str, openapi.OperationVerb, openapi.OperationObject]:
    req = endpoint.request
    method = openapi.OperationVerb.fromStr(req['method'].lower())
    summary = req['name'] + ': ' + req['summary']
    description = req['description']
    parameters = toParameterObjects(req.get('urlParams', []), req.get('queryParams', []))
    reqestBody = toRequestBodyObjects(req.get('formParams', []))
    responses = toResponsesObject(endpoint.response)
    op = openapi.OperationObject(responses, summary, description, parameters, reqestBody)
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
        schemaObjects = {o.typename:toSchemaObjectFromCommonObject(o) for o in api.commonObjects()}
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

    #for i in api.endpoints():
    #    print(i)
    #for i in api.commonObjects():
    #    print(i)

    converter = OpenApiConverter()
    oa = converter.convert(appname[0].upper() + appname[1:], '1.0.0-20191003', api)
    #print(oa.toJson())
    print(json.dumps(oa.toJson()))

if __name__ == '__main__':
    main()
    
