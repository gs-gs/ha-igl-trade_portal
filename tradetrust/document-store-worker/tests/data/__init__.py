from string import Template


with open('/document-store-worker/tests/data/document.v2.json', 'rt') as f:
    DOCUMENT_V2_TEMPLATE = Template(f.read())


with open('/document-store-worker/tests/data/document.v3.json', 'rt') as f:
    DOCUMENT_V3_TEMPLATE = Template(f.read())
