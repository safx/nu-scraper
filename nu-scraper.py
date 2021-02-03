#!/usr/bin/env python

from collections import OrderedDict
from pyquery import PyQuery as pq
import sys
import json
import os


class ParamInfo(object):
    def __init__(self, trElement, optionalChecker):
        tds = [pq(trElement)('td').eq(j).text() for j in range(3)]
        ns = [e[:-1] if len(e) > 0 and e[-1] == ',' else e for e in tds[0].split()]
        self.name = ns[0]
        self.optional = optionalChecker(ns)
        self.array = False
        self.typename = tds[1]
        self.description = tds[2]

        self.validVariableName = True
        name = self.name
        if name[-3:] == '[0]':
            self.array = True
            self.name = name[:-3]
        elif name[-2:] == '[]':
            self.array = True
            self.name = name[:-2]
        elif name.find('[0]') >= 0:
            self.validVariableName = False
        # Hack: wrong tyename
        if self.name == 'projectIdOrKey' and self.typename == 'Number':
            self.typename = 'String'

    @property
    def obj(self):
        obj = OrderedDict()
        obj["name"] = self.name
        obj["optional"] = self.optional
        obj["array"] = self.array
        obj["type"] = self.typename
        obj["description"] = self.description
        return obj

    def __repr__(self):
        return '(%s, %s, %s, %s)' % (self.name, str(self.optional), self.typename, self.description)



class WebAPI(object):
    def __init__(self, appName, hyphenName, summary, description, method, url, scope, urlParams, formParams, queryParams, response, apiDocumentUrl):
        self.appName = appName
        self.hyphenName = hyphenName
        self.summary = summary
        self.description = description
        self.method = method
        self.url = url
        self.scope = scope
        self.urlParams = urlParams
        self.formParams = formParams
        self.queryParams = queryParams
        self.response = response
        self.apiDocumentUrl = apiDocumentUrl

    @property
    def cameCaeeName(self):
        def toCamelCase(name):
            return ''.join([e[0].upper() + e[1:] for e in name.split('-')])
        return toCamelCase(self.hyphenName)

    def writeAPIJson(self, lang = 'en'):
        obj = OrderedDict()
        obj["name"] = self.cameCaeeName
        obj["summary"] = self.summary
        if self.description: obj["description"] = self.description
        obj["method"] = self.method
        obj["url"] = self.url
        obj["scope"] = self.scope
        if len(self.urlParams): obj["urlParams"] = [e.obj for e in self.urlParams]
        if len(self.formParams): obj["formParams"] = [e.obj for e in self.formParams]
        if len(self.queryParams): obj["queryParams"] = [e.obj for e in self.queryParams]
        obj["apiDocumentUrl"] = self.apiDocumentUrl

        outputName = os.path.join(self.appName, 'api', lang, self.hyphenName + '.json')
        with open(outputName, 'w') as f:
            json.dump(obj, f, indent=2)


    def validResponseJson(self): # => (object, err) or (str, err)
        s = self.response
        try:
            return (json.loads(s), '')
        except:
            s = s.replace(', ...', '')
            try:
                return (json.loads(s), 'fix ellipsis')
            except:
                s = s.replace('" "', '", "').replace('} "', '}, "').replace('}, }', '} }').replace('}, ]', '} ]')
                try:
                    return (json.loads(s), '⚠️ fix typo')
                except:
                    return (s, '⚠️ invalid JSON')

    def writeResponseJson(self):
        if self.response == None:
            return '(none response)'
        if self.response == 'Status Line / Response Header':
            return '(none response)'

        outputName = os.path.join(self.appName, 'response', self.hyphenName + '.json')
        with open(outputName, 'w') as f:
            (objOrStr, err) = self.validResponseJson()
            if type(objOrStr) != str:
                json.dump(objOrStr, f, sort_keys=True, indent=2)
            else:
                f.write(objOrStr)
            return '' if err == '' else '(%s)' % (err,)

def getWebAPI(appName, apiDocumentUrl):
    data = pq(url=apiDocumentUrl)
    optionalChecker = lambda ns: len(ns) > 1 and ns[-1] == '(Optional)'
    requredChecker  = lambda ns: len(ns) == 0 or ns[-1] != '(Required)'
    defaultChecker = requredChecker if appName == 'backlog' else optionalChecker

    def toBaseName(url):
        return url.split('/')[-1]

    def q(p, default=None):
        text = data(p).next().text()
        return default if text == '' else text

    def p(p, checker=defaultChecker):
        e = data(p).next()
        while not e.is_('table') and not e.is_('h2') and len(e.text()) > 0:
            e = e.next()
        return [ParamInfo(e, checker) for e in e('table > tbody > tr')]

    def c(p, default=None):
        node = data(p).next()
        if node.is_('pre'):
            text = node.text()
            return default if text == '' else text
        return None

    summary     = data('h1').text()
    descNode    = data('h1').next()
    description = '' if descNode.attr('id') == 'method' else descNode.text()
    method      = q('#method')
    url         = q('#url')
    scope       = q('#scope')
    urlParams   = p('#url-parameters', lambda ns: False)
    formParams  = p('#form-parameters')
    queryParams = p('#query-parameters')
    response    = c('#response-body', None) or c('#response-example', None) or c('#json-response-example')

    return WebAPI(appName, toBaseName(apiDocumentUrl), summary, description, method, url, scope, urlParams, formParams, queryParams, response, apiDocumentUrl)


SITE_ROOT = 'https://developer.nulab.com'
def getAppAPIs(appName, lang):
    top = pq(url=SITE_ROOT + '/docs/' + appName + '/')
    count = 199
    for i in top('a.sidebar__links'):
        path = i.get('href')
        if path[-1] == '/': path = path[:-1]

        if path.find('/docs/' + appName + '/api/') != 0 or path.find('/docs/typetalk/api/1/streaming') >= 0:
            continue

        api = getWebAPI(appName, SITE_ROOT + path)
        print("%-40s" % (api.cameCaeeName,), end='', flush=True)

        api.writeAPIJson(lang)
        res = api.writeResponseJson()
        print('✔︎ ' + res)

        count -= 1
        if count <= 0:
            break



def getAppAPIsByAppName(appNames, lang = 'en'):
    if len(appNames) == 1 and appNames[0] == 'all':
        appNames = [
            'typetalk',
            'backlog',
            'cacoo'
        ]
    for i in appNames:
        getAppAPIs(i, lang)


getAppAPIsByAppName(sys.argv[1:])
