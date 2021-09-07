module.exports = {
  "id": "SERIAL_NUMBER_123",
  "$template": {
    "name": "CUSTOM_TEMPLATE",
    "type": "EMBEDDED_RENDERER",
    "url": "https://localhost:3000/renderer"
  },
  "issuers": [
    {
      "name": "DEMO STORE",
      "tokenRegistry": "0x9178F546D3FF57D7A6352bD61B80cCCD46199C2d",
      "identityProof": {
        "type": "DNS-TXT",
        "location": "tradetrust.io"
      }
    }
  ],
  "recipient": {
    "name": "Recipient Name"
  },
  "unknownKey": "Some value",
  "data": {
  	"message": {
      "public": "Hello world!",
      "private": "No..."
    }
  }
}
