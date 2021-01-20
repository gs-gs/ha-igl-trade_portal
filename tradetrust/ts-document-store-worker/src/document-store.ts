import { ethers, Wallet} from 'ethers';
import {connect} from '@govtechsg/document-store';
import config from './config';
import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';

function connectWallet(): Wallet{
  const provider = new ethers.providers.JsonRpcProvider(config.BLOCKCHAIN_ENDPOINT)
  return new Wallet(config.DOCUMENT_STORE_OWNER_PRIVATE_KEY, provider);
}

async function connectDocumentStore(wallet: Wallet): Promise<DocumentStore>{
  return await connect(config.DOCUMENT_STORE_ADDRESS, wallet);
}

export {
  connectDocumentStore,
  connectWallet
}
