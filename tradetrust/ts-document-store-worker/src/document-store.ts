import { ethers, Wallet} from 'ethers';
import { IBatchedDocumentStoreTaskConfig } from 'src/config';
import { Keys } from 'src/repos';
import {connect} from '@govtechsg/document-store';
import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';

async function connectWallet(config: IBatchedDocumentStoreTaskConfig): Promise<Wallet>{
  const privateKey = await Keys.getStringOrB64KMS(config.DOCUMENT_STORE_OWNER_PRIVATE_KEY);
  const provider = new ethers.providers.JsonRpcProvider(config.BLOCKCHAIN_ENDPOINT)
  return new Wallet(privateKey, provider);
}

async function connectDocumentStore(config: IBatchedDocumentStoreTaskConfig, wallet: Wallet): Promise<DocumentStore>{
  return await connect(config.DOCUMENT_STORE_ADDRESS, wallet);
}

export {
  connectDocumentStore,
  connectWallet
}
