import _ from 'lodash';
import {
  DOCUMENT_STORE_ADDRESS
} from 'tests/env';
import documentV2Data from 'tests/data/document.v2.json';
import documentV3Data from 'tests/data/document.v3.json';

const documentV2 = ()=>{
  const document = _.cloneDeep(documentV2Data);
  document.issuers[0].documentStore = DOCUMENT_STORE_ADDRESS;
  return document;
}

const documentV3 = ()=>{
  const document = _.cloneDeep(documentV3Data);
  document.openAttestationMetadata.proof.value = `did:ethr:${DOCUMENT_STORE_ADDRESS}`;
  document.openAttestationMetadata.identityProof.identifier = document.openAttestationMetadata.proof.value;
  return document;
}


export {
  documentV2,
  documentV3
}
