module.exports = {
  "reference": "SERIAL_NUMBER_123",
  "name": "Singapore Driving Licence",
  "validFrom": "2010-01-01T19:23:24Z",
  "template": {
    "name": "CUSTOM_TEMPLATE",
    "type": "EMBEDDED_RENDERER",
    "url": "https://localhost:3000/renderer"
  },
  "issuer": {
    "id": "https://example.com",
    "name": "DEMO STORE",
    "identityProof": {
      "type": "DNS-TXT",
      "location": "tradetrust.io"
    }
  },
  "proof": {
    "type": "OpenAttestationSignature2018",
    "method": "DOCUMENT_STORE",
    "value": "0x9178F546D3FF57D7A6352bD61B80cCCD46199C2d"
  },
  "recipient": {
    "name": "Recipient Name"
  },
  "unknownKey": "Some value",
  "data": {
  	"message": {
      "public": "Hello world!",
      "private": "No..."
    }
  },
  "attachments": [
    {
      "type": "DocumentVerification2018",
      "filename": "sample.pdf",
      "mimeType": "application/pdf",
      "data": "BASE64_ENCODED_FILE"
    }
  ]
}
