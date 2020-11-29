#!/usr/bin/env python

from os import pread
import sys
import json
import re
import os
import copy
from collections import OrderedDict
import openapi
import ir


class OpenApiConverter:
    def convert(self, title: str, version: str, api: ir.API) -> openapi.OpenAPI:
        info = openapi.InfoObject(title, version)
        oa = openapi.OpenAPI(info=info)
        return oa


def main():
    appname = 'typetalk'
    api = ir.API.initWithDir(appname)
    api.findAndRegisterSimilarObjects()
    converter = OpenApiConverter()
    oa = converter.convert(appname[0].upper() + appname[1:], '1.0', api)
    print(oa.toJson())

if __name__ == '__main__':
    main()
    
