# Document API

Standard REST API allowing users to put certificates of origin
to the system and perform "issue" step.

Data model documentation can be taken from https://app.swaggerhub.com/apis-docs/gosource/coo/1 here.

Base url is `/api/documents/v0/` - please prepend to any API endpoint url. Installation-specific, version-specific value.

## How to perform the demo workflow

1. Get some API token
2. Send POST request to the https://trade.c2.devnet.trustbridge.io/api/documents/v0/CertificatesOfOrigin/ endpoint with body of the certificate to be created
3. Remember the certificate ID from the response (it's UUID somewhere)
4. Do things you need to do you bake your QR code into your PDF file and upload it as:
5. sending multipart/form data POST request to the https://trade.c2.devnet.trustbridge.io/api/documents/v0/CertificatesOfOrigin/YOUR_CERT_ID_HERE/attachment/ with the file attached as "file"
6. Perform issue step by sending empty POST request https://trade.c2.devnet.trustbridge.io/api/documents/v0/CertificatesOfOrigin/YOUR_CERT_ID_HERE/issue/
7. Wait a couple of minutes and observe that link from the certificate details `OA.url` becomes working and validated.

## Auth

All endpoints require correct auth.

* API token auth - go to your profile and create tokens for the current org/user. This is the preffered method
* Session auth - mainly to use from the web browser (JS applications/etc)
* Basic auth - less secure but is supported.
* custom auth methods - it's usually possible to add more custom auth methods (if the remote system update costs are greater than the trade portal).

## Endpoints

### Certificates list

`GET /CertificatesOfOrigin/`

Paginated. The each certificate is rendered using the short serializer.

Response example:

    {
      "count": 64,
      "next": "http://domain.name/api/documents/v0/CertificatesOfOrigin/?page=2",
      "previous": null,
      "results": [
        {
          "id": "e375c910-7110-40e3-9be0-629173ff9283",
          "document_number": "WBC7437483943",
          "created_at": "2020-09-15T18:51:23.622700+10:00"
        },
        ...
       ]
    }


### Certificate creation

`POST /CertificatesOfOrigin/`

Request example:

    {
        "certificateOfOrigin": {
          "id": "wcaaba9320",
          "issueDateTime": "2020-08-30T15:17:31.862Z",
          "name": "Certificate of Origin",
          "attachedFile": {
            "file": "(base 64 representation)",
            "encodingCode": "base64",
            "mimeCode": "application/pdf"
          },
          "firstSignatoryAuthentication": {
            "actualDateTime": "2020-08-30T15:17:31.862Z",
            "statement": "string",
            "providingTradeParty": {
                ...
            }
          },
          ...
        }
    }

Response: the same as the certificate detail, with 201 HTTP status code. Response contains the ID of the created object for further operations.

### Certificate detail

`GET /CertificatesOfOrigin/{id}/`

Contains next fields:

* certificateOfOrigin - see the Swagger
* id - internal certificate ID, for usage in the API (update/issue/etc the object)
* OA - dict of Open Attestation-related data containing:
  * URL - the text which is rendered to the QR code, which is usually a link to a verify page
  * qrcode - base64 representation of a rendered QR code with the same URL

Please note that if some binary PDF document is uploaded then it's rendered as base64 as well, so the response is considerably large. It's possible to work around it.

Response example:

    {
        "certificateOfOrigin": {...},
        "id": "88db0d99-c7f1-402e-8b4e-e616194ad9af",
        "OA": {
            "url": "http://domain.name/v/?q=%7B%22type%22%3A%20%22DOCUMENT%22%2C%20%22payload%22%3A%20%7B%22uri%22%3A%20%22http%3A//domain.name%3A8050/oa/33b1e669-7c13-454d-ac25-80f7f954f019/%22%2C%20%22key%22%3A%20%22FC0F19B0CE65C45471DCFA7D608E1FD678D0CD0C23469980F5FC38975ED10A5E%22%2C%20%22permittedActions%22%3A%20%5B%22VIEW%22%5D%2C%20%22redirect%22%3A%20%22https%3A//dev.tradetrust.io%22%7D%7D",
            "qrcode": "iVBORw0KGg....5CYII="
          }
    }

### Certificate update

`PATCH /CertificatesOfOrigin/{id}/`

Pass subset of fields you want to update (still included in the `certificateOfOrigin` dict).

Return value is equal to the certificate details endpoint and shows actual status of
the certificate saved to the database at the moment of update.

Request example:

    {
        "certificateOfOrigin": {
          "name": "XX7437488-new",
          "freeTradeAgreement": "China-Australia Free Trade Agreement"
        }
    }


### File upload

`POST /CertificatesOfOrigin/{id}/attachment/`

This is a multipart/form-data request instead of JSON one.

There are 2 parameters:

* file - the attachment
* metadata - JSON with any custom metadata, optional; you may use it if you want to save some extra info along the file. It's not practically used at this moment.

Request example:

    curl http://host/api/documents/v0/CertificatesOfOrigin/14a20633-34d6-4b71-9a32-cdcb8b095e1c/attachment/ \
    -F "file=@CHAFTA.pdf" \
    -F 'metadata={"a": "b"}'

Response: metadata

As a result the file is saved to the certificate body.

### Certificate issue

`POST /CertificatesOfOrigin/{id}/issue/`

Send a POST request here to start the issue process. It will notarize the document
and send IGL message (if needed).

From this point you may start checking the OA credentials for the fact of certificate
becoming issued (it usually takes some minutes).
