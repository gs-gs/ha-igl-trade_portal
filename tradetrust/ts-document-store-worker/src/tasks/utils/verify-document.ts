import {
  OPEN_ATTESTATION_VERSION_ID_V2_SHORT,
  OPEN_ATTESTATION_VERSION_ID_V3_SHORT,
  DOCUMENT_STORE_PROOF_TYPE
} from '../../constants';
import { wrapDocument, getData, validateSchema, verifySignature } from '@govtechsg/open-attestation';
import {
  SchemaId
} from '@govtechsg/open-attestation';
import { DocumentStore } from "@govtechsg/document-store/src/contracts/DocumentStore";

class VerificationError extends Error{

}


interface IVerifyDocumentProps{
  documentStore: DocumentStore
}

abstract class VerifyDocument{

  protected props: IVerifyDocumentProps;
  constructor(props:IVerifyDocumentProps){
    this.props = props;
  }


  getDocumentVersion(document: any): SchemaId.v2|SchemaId.v3|undefined{
    switch(document.version){
      case SchemaId.v2:
      case OPEN_ATTESTATION_VERSION_ID_V2_SHORT:
        return SchemaId.v2;
      case SchemaId.v3:
      case OPEN_ATTESTATION_VERSION_ID_V3_SHORT:
        return SchemaId.v3;
    }
  }

  getDocumentStoreAddress(document: any, version: SchemaId.v2|SchemaId.v3|undefined): string|undefined{
    if(version === SchemaId.v2){
      return document.issuers?.[0]?.documentStore;
    }else if(version === SchemaId.v3){
      return document.proof?.method===DOCUMENT_STORE_PROOF_TYPE?document.proof.value: undefined;
    }
    return undefined;
  }

  async verifyDocumentStoreAddress(document: any){
    const version = this.getDocumentVersion(document);
    const got = this.getDocumentStoreAddress(document, version);
    const expected = this.props.documentStore.address;
    if(expected != got){
      throw new VerificationError(`Invalid document store address. Expected: ${expected}. Got: ${got}`);
    }
  }

  async verifyWrappedDocumentSchema(document: any){
    if(!validateSchema(document)){
      throw new VerificationError('Invalid document schema');
    }
  }

  async verifyWrappedDocumentSignature(document: any){
    if(!verifySignature(document)){
      throw new VerificationError('Invalid document signature');
    }
  }

  async verifyUnwrappedDocumentSchema(document: any){
    try{
      wrapDocument(document)
    }catch(e){
      if(!!e.validationErrors){
        throw new VerificationError('Invalid document schema');
      }else{
        throw e;
      }
    }
  }

  async verifyDocumentNotRevoked(document: any){
    const targetHash = `0x${document.signature.targetHash}`;
    if(await this.props.documentStore.isRevoked(targetHash)){
      throw new VerificationError(`Document ${targetHash} already revoked`);
    }
  }

  abstract verify(document: any): Promise<void>;
}


class VerifyDocumentRevocation extends VerifyDocument{
  async verify(document: any){
    await this.verifyWrappedDocumentSchema(document);
    await this.verifyWrappedDocumentSignature(document);
    await this.verifyDocumentStoreAddress(getData(document));
    await this.verifyDocumentNotRevoked(document);
  }
}

class VerifyDocumentIssuance extends VerifyDocument{
  async verify(document: any){
    await this.verifyUnwrappedDocumentSchema(document);
    await this.verifyDocumentStoreAddress(document);
  }
}


export {
  VerifyDocument,
  VerifyDocumentIssuance,
  VerifyDocumentRevocation,
  VerificationError
}
