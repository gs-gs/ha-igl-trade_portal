import {
  utils,
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
  public details: string | undefined;
  constructor(message: string, details?: string){
    super(message);
    this.details = details;
  }
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

  async verifyDocumentVersionV2(document: any){
    const version = this.getDocumentVersion(document);
    if(version != SchemaId.v2){
      throw new VerificationError('Invalid document version');
    }
  }

  async verifyDocumentVersionV3(document: any){
    const version = this.getDocumentVersion(document);
    if(version != SchemaId.v3){
      throw new VerificationError('Invalid document version');
    }
  }

  getDocumentStoreAddressV2(document: any): string|undefined{
    return document.issuers?.[0]?.documentStore;
  }

  getDocumentStoreAddressV3(document: any): string|undefined{
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

  async verifyDocumentStoreAddressV2(document: any){
    const got = this.getDocumentStoreAddressV2(document);
    const expected = this.props.documentStore.address;
    if(got != expected){
      throw new VerificationError(`Invalid document store address. Expected: ${expected}. Got: ${got}`);
    }
  }

  async verifyDocumentStoreAddressV3(document: any){
    const got = this.getDocumentStoreAddressV3(document);
    const expected = this.props.documentStore.address;
    if(got != expected){
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
        throw new VerificationError('Invalid document schema', JSON.stringify(e.validationErrors));
      }else{
        throw e;
      }
    }
  }

  async verifyUnwrappedDocumentSchemaV3(document: any){
    try{
      await wrapDocumentV3(document);
    }catch(e){
      if(!!e.validationErrors){
        throw new VerificationError('Invalid document schema',JSON.stringify(e.validationErrors));
      }else{
        throw e;
      }
    }
  }

  async verifyWrappedDocumentV2(document: any){
    if(!utils.isWrappedV2Document(document)){
      throw new VerificationError('Document not wrapped');
    }
  }

  async verifyNotWrappedDocumentV2(document: any){
    if(utils.isWrappedV2Document(document)){
      throw new VerificationError('Document is wrapped');
    }
  }

  async verifyWrappedDocumentV3(document: any){
    if(!utils.isWrappedV3Document(document)){
      throw new VerificationError('Document not wrapped');
    }
  }

  async verifyNotWrappedDocumentV3(document: any){
    if(utils.isWrappedV3Document(document)){
      throw new VerificationError('Document is wrapped');
    }
  }

  async verifyDocumentRevocable(document: any){
    if(!utils.isDocumentRevokable(document)){
      throw new Error('Document not revocable');
    }
  }

  async verifyDocumentNotRevokedV2(document: any){
    const targetHash = `0x${document.signature.targetHash}`;
    if(await this.props.documentStore.isRevoked(targetHash)){
      throw new VerificationError(`Document ${targetHash} already revoked`);
    }
  }

  async verifyDocumentNotRevokedV3(document: any){
    const targetHash = `0x${document.proof.targetHash}`;
    if(await this.props.documentStore.isRevoked(targetHash)){
      throw new VerificationError(`Document ${targetHash} already revoked`);
    }
  }
  abstract verify(document: any): Promise<void>;
}


class VerifyDocumentRevocationV2 extends VerifyDocument{
  async verify(document: any){
    await this.verifyDocumentVersionV2(document);
    await this.verifyWrappedDocumentV2(document);
    await this.verifyDocumentRevocable(document);
    await this.verifyWrappedDocumentSchema(document);
    await this.verifyWrappedDocumentSignature(document);
    await this.verifyDocumentStoreAddressV2(getData(document));
    await this.verifyDocumentNotRevokedV2(document);
  }
}


class VerifyDocumentIssuanceV2 extends VerifyDocument{
  async verify(document: any){
    await this.verifyDocumentVersionV2(document);
    await this.verifyNotWrappedDocumentV2(document);
    await this.verifyUnwrappedDocumentSchemaV2(document);
    await this.verifyDocumentStoreAddressV2(document);
  }
}


class VerifyDocumentRevocationV3 extends VerifyDocument{
  async verify(document: any){
    await this.verifyDocumentVersionV3(document);
    await this.verifyWrappedDocumentV3(document);
    await this.verifyDocumentRevocable(document);
    await this.verifyWrappedDocumentSchema(document);
    await this.verifyWrappedDocumentSignature(document);
    await this.verifyDocumentStoreAddressV3(document);
    await this.verifyDocumentNotRevokedV3(document);
  }
}


class VerifyDocumentIssuanceV3 extends VerifyDocument{
  async verify(document: any){
    await this.verifyDocumentVersionV3(document);
    await this.verifyNotWrappedDocumentV3(document);
    await this.verifyUnwrappedDocumentSchemaV3(document);
    await this.verifyDocumentStoreAddressV3(document);
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
