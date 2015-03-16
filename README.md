# amanuensis
A quick script to generate ebooks from Reddit

Takes a list of URLs and chapter headings, returns formatted XHTML with a mainfest and ToC. Not the most elegant thing in the world, but it does the job - expect a substantial cleanup in the near future.

Run using:
`python scripts/build_epub.py /path/to/layout.json`

Sample input JSON:
```json
{"title": "The Complete Works of Someone",
 "contents":
    [{"url": "http://www.example.com/foo/bar/", "title": "The Tale of Foo and Bar"},
     {"url": "http://www.example.com/gorillas/", "title": "Suddenly, a Gorilla"}]}}
```
