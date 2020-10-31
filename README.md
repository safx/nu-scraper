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

## generate source files for API client

./generate-rust-source-files.py 