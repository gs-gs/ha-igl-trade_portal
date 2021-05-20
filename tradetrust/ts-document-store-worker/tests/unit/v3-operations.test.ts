import { documentV3 } from 'tests/utils';
import {
  __unsafe__use__it__at__your__own__risks__wrapDocument as wrapDocument,
  __unsafe__use__it__at__your__own__risks__wrapDocuments as wrapDocuments
} from '@govtechsg/open-attestation';

describe.skip('OA V3 operations test', ()=>{
  test('wrap', async ()=>{
    const document = {
      unwrapped: documentV3(),
      wrapped: undefined
    };
    document.wrapped = await wrapDocument(document.unwrapped);
  });
});
