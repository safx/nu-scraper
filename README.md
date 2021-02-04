# nu-scraper

## scraping from developer site
The following commands fetch API information and save JSON files of API information and response to {service}/api and {service}/response respectively.
```
./nu-scraper.py backlog
./nu-scraper.py typetalk ja
```

## generate OpenAPI schema
The following commands outputs OpenAPI schema with collected information.
```
./generate-openapi.py backlog ja https://yourspace.backlog.com
./generate-defined-types.py en typetalk
```

The generated infomation might be incomplete and accurate to be fixed.

