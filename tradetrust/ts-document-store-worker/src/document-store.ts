import { ethers, Wallet} from 'ethers';
import {connect} from '@govtechsg/document-store';
import config from './config';
import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';

async function connectDocumentStore(): Promise<DocumentStore>{
  const provider = new ethers.providers.JsonRpcProvider(config.BLOCKCHAIN_ENDPOINT)
  const signer = new Wallet(config.DOCUMENT_STORE_OWNER_PRIVATE_KEY, provider);
  return await connect(config.DOCUMENT_STORE_ADDRESS, signer);
}

export {
  connectDocumentStore
}
