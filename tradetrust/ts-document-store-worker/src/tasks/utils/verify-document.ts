import {
  getData,
  validateSchema,
  verifySignature,
  wrapDocument as wrapDocumentV2,
  __unsafe__use__it__at__your__own__risks__wrapDocument as wrapDocumentV3
} from '@govtechsg/open-attestation';
import {
  SchemaId
} from '@govtechsg/open-attestation';
import { DocumentStore } from "@govtechsg/document-store/src/contracts/DocumentStore";
import {
  OPEN_ATTESTATION_VERSION_ID_V2_SHORT,
  OPEN_ATTESTATION_VERSION_ID_V3_SHORT,
  DOCUMENT_STORE_PROOF_TYPE,
  DID_PROOF_TYPE,
  REVOCATION_STORE_REVOCATION_TYPE
} from 'src/constants';


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
      const metadata = document.openAttestationMetadata??{};
      const proofMethod = metadata.proof?.method;
      const proofValue:string = metadata.proof?.value;
      const revocationType = metadata.proof?.revocation?.type;
      if(proofMethod == DOCUMENT_STORE_PROOF_TYPE){
        return proofValue;
      }else if(proofMethod == DID_PROOF_TYPE && revocationType == REVOCATION_STORE_REVOCATION_TYPE){
        return proofValue.split(':').pop();
      }
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

  async verifyUnwrappedDocumentSchemaV2(document: any){
    try{
      wrapDocumentV2(document)
    }catch(e){
      if(!!e.validationErrors){
        throw new VerificationError('Invalid document schema');
      }else{
        throw e;
      }
    }
  }

  async verifyUnwrappedDocumentSchemaV3(document: any){
    try{
      await wrapDocumentV3(document);
    }catch(e){
      // TODO: decide what to do for better error handling here,
      // maybe add logging
      throw new VerificationError(`Invalid document schema`);
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


class VerifyDocumentRevocationV2 extends VerifyDocument{
  async verify(document: any){
    await this.verifyWrappedDocumentSchema(document);
    await this.verifyWrappedDocumentSignature(document);
    await this.verifyDocumentStoreAddress(getData(document));
    await this.verifyDocumentNotRevoked(document);
  }
}


class VerifyDocumentIssuanceV2 extends VerifyDocument{
  async verify(document: any){
    await this.verifyUnwrappedDocumentSchemaV2(document);
    await this.verifyDocumentStoreAddress(document);
  }
}


class VerifyDocumentRevocationV3 extends VerifyDocument{
  async verify(document: any){
    await this.verifyWrappedDocumentSchema(document);
    await this.verifyWrappedDocumentSignature(document);
    await this.verifyDocumentStoreAddress(document);
    await this.verifyDocumentNotRevoked(document);
  }
}


class VerifyDocumentIssuanceV3 extends VerifyDocument{
  async verify(document: any){
    await this.verifyUnwrappedDocumentSchemaV3(document);
    await this.verifyDocumentStoreAddress(document);
  }
}

export {
  VerifyDocument,
  VerifyDocumentIssuanceV2,
  VerifyDocumentRevocationV2,
  VerifyDocumentIssuanceV3,
  VerifyDocumentRevocationV3,
  VerificationError
}
