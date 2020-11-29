# nu-scraper

## scraping from developer site
The following commands fetch API information and save JSON files of API information and response to {service}/api and {service}/response respectively.
```
./nu-scraper.py backlog
./nu-scraper.py typetalk
./nu-scraper.py all
```

## generate defined types
The following commands collect same object and save {service}/defnined-types.json as API's defined types.
```
./generate-defined-types.py backlog
./generate-defined-types.py typetalk
```

Some type infomation in the generated files are incomplete and need to be fixed to collect type information in order to generate source codes in the next step.

## generate source files for API client

./generate-rust-source-files.py 


"someProp" { type, [required | default] }
"_file"

```
    "Point": {
        "x": { "type": "number", "required": true },
        "y": { "type": "number", "default": 0 }        
    }
```



```
    "Point": {
        "type": "object",
        "required": [ "x" ],
        "properties": {
          "x": { "type": "number", format: "int64" },
          "y": { "type": "number", "default": 0 }        
        }
    }
```

## Supported Swagger schemas

https://swagger.io/specification/

- OpenAPI Object
    - openapi
    - info
    - paths
    - components
- Info Object
    - title
    - version
- Paths Object
    - get
    - put
    - post
    - delete
    - patch
- Path Item Object
- Component Object
    - schemas
- Reference Object
    - $ref
- Schema Object
    - title
    - type
    - required
    - nullable
    - items
    - properties
    - format
    - default
    - description
- Media Type Object
- Data Types
