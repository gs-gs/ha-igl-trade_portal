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
  document.proof.value = DOCUMENT_STORE_ADDRESS;
  return document;
}


export {
  documentV2,
  documentV3
}
