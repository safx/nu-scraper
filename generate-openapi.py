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

def toSchemaObject(v: ir.TypeBase) -> Union[openapi.SchemaObject, openapi.ReferenceObject]:
    if type(v) == ir.ArrayType:
        return openapi.SchemaObject(type=openapi.DataType.array, items=toSchemaObject(v.type))
    elif type(v) == ir.ObjectType:
        props = {k:toSchemaObject(v) for (k,v) in v.items()}
        return openapi.SchemaObject(properties=props)
    elif type(v) == ir.Nullable:
        s = toSchemaObject(v.type)
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
    elif v is None:
        return openapi.PrimitiveDataType.string.toSchemaObject() # FIXME: we assume an unguessable object as string

    return openapi.ReferenceObject('#/components/schemas/' + v.typename) # FIXME: ref path

def toSchemaObjectFromCommonObject(cobj: ir.CommonObjectType) -> openapi.SchemaObject:
    props = {k:toSchemaObject(v) for (k,v) in cobj.object.items()}
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
        array = p['array']
        if array:
            name += '[]'
        if required:
            reqs.append(name)
    return openapi.SchemaObject(properties=props, required=reqs if len(reqs) > 0 else None)

def toParameterObject(params: Dict[str, str], location: openapi.ParameterLocation) -> openapi.ParameterObject:
    name = params['name']
    required = not params['optional']
    schema = toPrimitiveDataTypeFromStr(params['type']).toSchemaObject()
    description = params['description']
    array = params['array']
    if array:
        name += '[]'
    return openapi.ParameterObject(name, location, required, schema, description, array)

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

def toResponsesObject(response: ir.TypeBase, example) -> Optional[openapi.ResponsesObject]:
    if type(response) == ir.NullType:
        return openapi.ResponsesObject({'200': openapi.ResponseObject('Empty content')})

    content = {}
    content['application/json'] = openapi.MediaTypeObject(toSchemaObject(response), example)

    responses = {}
    responses['200'] = openapi.ResponseObject('TODO: response description', content=content)
    return openapi.ResponsesObject(responses)

def toPath(url: str, serverUrl: str) -> str:
    def toTemplate(c: str) -> str:
        if len(c) > 0 and c[0] == ':':
            return '{' + c[1:] + '}'
        elif len(c) > 0 and c[:2] == '@:': # FIXME: handle for spacical case
            return '@{' + c[2:] + '}'
        return c

    path = url[len(serverUrl):] if url.find(serverUrl) == 0 else url
    comp = [toTemplate(c) for c in path.split('/')]
    return '/'.join(comp)

def toOperationObjectTuple(endpoint: ir.Endpoint, serverUrl: str) -> Tuple[str, openapi.OperationVerb, openapi.OperationObject]:
    req = endpoint.request
    name = req['name']
    method = openapi.OperationVerb.fromStr(req['method'].lower())
    summary = name + ': ' + req['summary']
    description = req.get('description', '') + ' <br/>\nLink: [Original API document](' + req['apiDocumentUrl'] + ')'
    parameters = toParameterObjects(req.get('urlParams', []), req.get('queryParams', []))
    reqestBody = toRequestBodyObjects(req.get('formParams', []))
    responses = toResponsesObject(endpoint.response, endpoint.rawResponse)
    scope = req['scope']
    if scope is None:
        scope = 'backlog' # FIXME
    security = openapi.SecurityRequirementObject({'apikey' : [scope], 'oauth': [scope]}) if scope != '' else None
    operationId = name
    #tags = [scope]
    op = openapi.OperationObject(responses, summary, description, parameters, reqestBody, operationId, security)
    path = toPath(req['url'], serverUrl)
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
    def convert(self, title: str, version: str, serverUrl: str, api: ir.API, securitySchemes: openapi.SecuritySchemeObject) -> openapi.OpenAPI:
        schemaObjects = {o.typename:toSchemaObjectFromCommonObject(o) for o in api.commonObjects()}
        endpoints = [toOperationObjectTuple(e, serverUrl) for e in api.endpoints()]

        info = openapi.InfoObject(title, version)
        comps = openapi.ComponentsObject(schemaObjects, securitySchemes=securitySchemes)
        paths = openapi.PathsObject(toPathsDict(endpoints))
        servers = [openapi.ServerObject(serverUrl)]
        oa = openapi.OpenAPI(info=info, paths=paths, components=comps, servers=servers)
        return oa

def createSecuritySchemeObjects(appname, backlogUrl):
    if appname == 'typetalk':
        authUrl = 'https://typetalk.com/oauth2/authorize'
        tokenUrl = 'https://typetalk.com/oauth2/access_token'
        scopes = {
            'topic.read': 'Get messages in topics',
            'topic.post': 'Post messages to topics and like messages',
            'topic.write': 'Create and update topics',
            'topic.delete': 'Delete topics',
            'my': 'Get topic list, profile, notifications and save bookmarks'
        }
        authorizationCode = openapi.OAuthFlowObject(authUrl, tokenUrl, scopes, tokenUrl)
        clientCredentials = openapi.OAuthFlowObject(tokenUrl=tokenUrl, scopes=scopes, refreshUrl=tokenUrl)
        flows = openapi.OAuthFlowsObject(authorizationCode=authorizationCode, clientCredentials=clientCredentials)
        return {
            'apikey' : openapi.SecuritySchemeObject(type='apiKey', name='X-Typetalk-Token', locatedIn='header'),
            'oauth': openapi.SecuritySchemeObject(type='oauth2', flows=flows)
        }
    elif appname == 'backlog':
        authUrl = backlogUrl + '/OAuth2AccessRequest.action'
        tokenUrl = backlogUrl + '/api/v2/oauth2/token'
        scopes = {'backlog': 'backlog'}
        authorizationCode = openapi.OAuthFlowObject(authUrl, tokenUrl, scopes, tokenUrl)
        clientCredentials = openapi.OAuthFlowObject(tokenUrl=tokenUrl, scopes=scopes, refreshUrl=tokenUrl)
        flows = openapi.OAuthFlowsObject(authorizationCode=authorizationCode, clientCredentials=clientCredentials)
        return {
            'apikey' : openapi.SecuritySchemeObject(type='apiKey', name='apiKey', locatedIn='query'),
            'oauth': openapi.SecuritySchemeObject(type='oauth2', flows=flows)
        }
    else:
        assert('Unknwon app name' and False)

def main(appname, serverUrl = 'https://typetalk.com/api'):
    api = ir.API.initWithDir(appname)
    api.findAndRegisterSimilarObjects()

    #for i in api.endpoints():
    #    print(i)
    #for i in api.commonObjects():
    #    print(i)

    converter = OpenApiConverter()
    oa = converter.convert(appname[0].upper() + appname[1:], '1.0.0-20210127', serverUrl, api, createSecuritySchemeObjects(appname, serverUrl))
    #print(oa.toJson())
    print(json.dumps(oa.toJson()))

if __name__ == '__main__':
    main(*sys.argv[1:])
