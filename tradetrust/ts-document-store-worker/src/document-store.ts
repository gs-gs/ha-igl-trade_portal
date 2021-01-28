import { ethers, Wallet} from 'ethers';
import config from './config';
import { Keys } from './repos';
import {connect} from '@govtechsg/document-store';
import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';

async function connectWallet(): Promise<Wallet>{
  const privateKey = await Keys.getStringOrB64KMS(config.DOCUMENT_STORE_OWNER_PRIVATE_KEY);
  const provider = new ethers.providers.JsonRpcProvider(config.BLOCKCHAIN_ENDPOINT)
  return new Wallet(privateKey, provider);
}

async function connectDocumentStore(wallet: Wallet): Promise<DocumentStore>{
  return await connect(config.DOCUMENT_STORE_ADDRESS, wallet);
}

export {
  connectDocumentStore,
  connectWallet
}
