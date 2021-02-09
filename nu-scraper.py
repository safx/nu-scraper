#!/usr/bin/env python

from collections import OrderedDict
from pyquery import PyQuery as pq
import sys
import json
import os


class ParamInfo(object):
    def __init__(self, trElement, optionalChecker):
        def conv(typename):
            dic = {
                '数値': 'Number',
                '文字列': 'String',
                '真偽値': 'Boolean',
                '日付時刻': 'DateTime',
                'バイナリ': 'Binary',
                '文字列(固定)': 'String',
                'String(Fixed)': 'String',
            }   
            return dic.get(typename, typename)

        tds = [pq(trElement)('td').eq(j).text() for j in range(3)]
        ns = [e[:-1] if len(e) > 0 and e[-1] == ',' else e for e in tds[0].split()]
        self.name = ns[0]
        self.optional = optionalChecker(ns)
        self.array = False
        self.typename = conv(tds[1])
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
    def __init__(self, appName, hyphenName, summary, description, method, url, scope, urlParams, formParams, queryParams, response, apiDocumentUrl, roles):
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
        self.roles = roles

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
        if self.roles: obj["roles"] = self.roles
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

def getWebAPI(appName, apiDocumentUrl, lang = 'en'):
    def dic(key):
        if lang == 'en': return key
        dic = {
            # en -> ja
            'method': 'メソッド',
            'scope': 'スコープ',
            'role': '権限',
            'url-parameters': 'urlパラメーター',
            'url-parameters-alt': 'urlパラメータ',
            'url-parameters-alt2': 'url-パラメーター',
            'query-parameters': 'クエリパラメーター',
            'form-parameters': 'フォームパラメーター',
            'form-parameters-alt': 'リクエストパラメーター',
            #'response-body': 'レスポンス例',
            #'response-example': 'レスポンスの例',
            '(Optional)': '(任意)',
            '(Required)': '(必須)',
            # ja -> en
            '管理者': 'Administrator',
            '一般ユーザー': 'Normal User',
            'レポーター': 'Reporter',
            'ゲストレポーター': 'Guest Reporter',
        }   
        return dic.get(key, key)

    data = pq(url=apiDocumentUrl)
    optionalChecker = lambda ns: len(ns) > 1 and ns[-1] == dic('(Optional)')
    requredChecker  = lambda ns: len(ns) == 0 or ns[-1] != dic('(Required)')
    defaultChecker = requredChecker if appName == 'backlog' else optionalChecker

    def toBaseName(url):
        return url.split('/')[-1]

    def q(p, default=None, squash_space=True):
        text = data(p).next().text(squash_space=squash_space)
        return default if text == '' else text

    def p(p, checker=defaultChecker):
        e = data(p).next()
        while not e.is_('table') and not e.is_('h2') and len(e.text()) > 0:
            e = e.next()
        return [ParamInfo(e, checker) for e in e('table > tbody > tr')]

    def c(p, default=None):
        node = data(p).next()
        while not node.is_('pre') and node.length > 0:
            node = node.next()
        if node.is_('pre'):
            text = node.text()
            return default if text == '' else text
        return None

    summary     = data('h1').text()
    descNode    = data('h1').next()
    description = '' if descNode.attr('id') == dic('method') else descNode.text()
    role        = q('#' + dic('role'), squash_space=False)
    roles       = None if role is None else [dic(e.strip()) for e in role.strip().split('\n')]
    method      = q('#' + dic('method'))
    url         = q('#' + dic('url'))
    scope       = q('#' + dic('scope')) or q('#scope')
    urlParams   = p('#' + dic('url-parameters'), lambda ns: False) or p('#' + dic('url-parameters-alt'), lambda ns: False) or p('#' + dic('url-parameters-alt2'), lambda ns: False)
    formParams  = p('#' + dic('form-parameters')) or p('#' + dic('form-parameters-alt'))
    queryParams = p('#' + dic('query-parameters'))
    response    = c('#' + dic('response-body'), None) or c('#' + dic('response-example'), None) or c('#' + dic('json-response-example'))

    return WebAPI(appName, toBaseName(apiDocumentUrl), summary, description, method, url, scope, urlParams, formParams, queryParams, response, apiDocumentUrl, roles)


SITE_ROOT = 'https://developer.nulab.com'
def getAppAPIs(appName, lang):
    rootUrl = SITE_ROOT + ('' if lang == 'en' else ('/' + lang)) + '/docs/' + appName + '/'
    top = pq(url=rootUrl)
    count = 199
    for i in top('a.sidebar__links'):
        path = i.get('href')
        if path[-1] == '/': path = path[:-1]

        if path.find('/docs/' + appName + '/api/') < 0 or path.find('/docs/typetalk/api/1/streaming') >= 0:
            continue

        api = getWebAPI(appName, SITE_ROOT + path, lang)
        print("%-40s" % (api.cameCaeeName,), end='', flush=True)

        api.writeAPIJson(lang)
        res = api.writeResponseJson()
        print('✔︎ ' + res)

        count -= 1
        if count <= 0:
            break



def getAppAPIsByAppName(appNames, lang = 'en'):
    getAppAPIs(appNames, lang)


getAppAPIsByAppName(*sys.argv[1:])
