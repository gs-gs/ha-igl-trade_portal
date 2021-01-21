import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import { Wallet } from 'ethers';
import { logger } from '../logger';
import { Batch } from './data';
import { Task } from './interfaces';
// TODO: add gas price updates
// TODO: add stuck transaction handling
class IssueBatch implements Task<void>{

  constructor(
    private wallet: Wallet,
    private documentStore: DocumentStore,
    private batch: Batch
  ){}

  async getTransactionParameters(){
    logger.debug('getTransactionParameters')
    const gasLimit = 1000000;
    const gasPrice = await this.wallet.getGasPrice();
    const nonce = await this.wallet.getTransactionCount('latest');
    return {
      gasLimit,
      gasPrice,
      nonce
    }
  }

  async next(): Promise<boolean>{
    logger.debug('next');
    const transactionParameters = await this.getTransactionParameters();

    const merkleRoot = '0x'+this.batch.merkleRoot;

    logger.debug('documentStore.populateTransaction.issue')
    const transaction = await this.documentStore.populateTransaction.issue(merkleRoot, transactionParameters);
    logger.debug('wallet.sendTransaction')
    const transactionResponse = await this.wallet.sendTransaction(transaction);
    logger.debug('transactionResponse.wait');
    const transactionReceipt = await transactionResponse.wait();
    return true;
  }

  async start(){
    logger.debug('start');
    while(!await this.next()){
      // update gas price code goes here
    }
  }
}


export default IssueBatch;
