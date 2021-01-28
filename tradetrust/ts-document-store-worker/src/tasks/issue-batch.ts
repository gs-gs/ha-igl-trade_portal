import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import { Wallet } from 'ethers';
import { logger } from '../logger';
import { Batch } from './data';
import { Task } from './interfaces';

class IssueBatch implements Task<void>{

  private currentGasPriceMultiplier: number = 1

  constructor(
    private wallet: Wallet,
    private documentStore: DocumentStore,
    private batch: Batch,
    private gasPriceMultiplier: number = 1.2,
    private transactionConfirmationThreshold: number = 12,
    private transactionTimeoutSeconds: number = 180
  ){}

  async next(): Promise<boolean>{
    logger.debug('next');
    let transactionResponse: any | undefined;
    try{
      const merkleRoot = '0x'+this.batch.merkleRoot;

      logger.debug('documentStore.populateTransaction.issue')
      const transaction = await this.documentStore.populateTransaction.issue(merkleRoot);
      transaction.gasLimit = await this.wallet.estimateGas(transaction);
      transaction.gasPrice = (await this.wallet.getGasPrice()).mul(this.currentGasPriceMultiplier);
      transaction.nonce = await this.wallet.getTransactionCount('latest');
      logger.info('transaction %O', transaction)

      logger.debug('wallet.sendTransaction')
      transactionResponse = await this.wallet.sendTransaction(transaction);
      logger.debug('wallet.provider.waitForTransaction');
      const transactionReceipt = await this.wallet.provider.waitForTransaction(
        transactionResponse.hash,
        this.transactionConfirmationThreshold,
        this.transactionTimeoutSeconds * 1000
      )
      return transactionReceipt !== undefined;
    }catch(e){
      // this is the only way these errors can be handled, ugly, but only
      if(e.message.startsWith('timeout exceeded')){
        logger.debug('error.message == "timeout exceeded ..."')
        return false;
      }
      // this error indicates that previos transaction was completed
      if(e.message.includes('Only hashes that have not been issued can be issued')){
        logger.debug('previos transaction completed succesfully');
        return true;
      }
      throw e;
    }
  }

  async start(){
    logger.debug('start');
    while(!await this.next()){
      // increasing gas price multiplier to resubmit a stuck transaction
      logger.info('transaction timed out, increasing gas price');
      this.currentGasPriceMultiplier *= this.gasPriceMultiplier;
      logger.debug('currentGasPriceMultiplier x gasPriceMultiplier = %s', this.currentGasPriceMultiplier);
    }
  }
}


export default IssueBatch;
