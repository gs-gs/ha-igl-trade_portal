import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import { Wallet } from 'ethers';
import { logger } from '../logger';
import { Batch } from './data';
import { Task } from './interfaces';

class IssueBatch implements Task<void>{

  private currentGasPriceMultiplier: number = 1;
  private pendingTransaction: any;

  constructor(
    private wallet: Wallet,
    private documentStore: DocumentStore,
    private batch: Batch,
    private gasPriceMultiplier: number = 1.2,
    private transactionConfirmationThreshold: number = 12,
    private transactionTimeoutSeconds: number = 180
  ){}

  isTransactionTimeoutError(e: any){
    logger.debug('isTransactionTimeoutError');
    return e.message.startsWith('timeout exceeded');
  }

  isHashDuplicationError(e: any){
    logger.debug('isHashDuplicationError');
    return e.message.includes('Only hashes that have not been issued can be issued');
  }


  async waitForTransaction(hash: string): Promise<boolean>{
    logger.debug('waitForTransaction');
    try{
      const transactionReceipt = await this.wallet.provider.waitForTransaction(
        hash,
        this.transactionConfirmationThreshold,
        this.transactionTimeoutSeconds * 1000
      )
      return transactionReceipt !== undefined;
    }catch(e){
      if(this.isTransactionTimeoutError(e)){
        return false;
      }
      throw e;
    }
  }

  async createIssueDocumentTransaction(merkleRoot: string){
    const transaction = await this.documentStore.populateTransaction.issue(merkleRoot);
    transaction.gasLimit = await this.wallet.estimateGas(transaction);
    transaction.gasPrice = (await this.wallet.getGasPrice()).mul(this.currentGasPriceMultiplier);
    transaction.nonce = await this.wallet.getTransactionCount('latest');
    return transaction;
  }

  async next(): Promise<boolean>{
    logger.debug('next');
    const merkleRoot = '0x'+this.batch.merkleRoot;
    logger.info(
      'Creating transaction for DocumentStore(%s).issue("%s")',
      this.documentStore.address,
      merkleRoot
    )
    try{
      const transaction = await this.createIssueDocumentTransaction(merkleRoot);
      logger.info('Transaction created');
      logger.info(transaction);
      logger.info('Sending transaction...');
      this.pendingTransaction = await this.wallet.sendTransaction(transaction);
    }catch(e){
      // this error indicates that previos transaction was completed
      // but we still want to have certain number of confirmation for it
      // before we consider it successful
      if(this.isHashDuplicationError(e)){
        logger.info('Previos transaction completed succesfully, can not create a new one');
      }else{
        throw e;
      }
    }
    logger.info(
      'Waiting for transaction to complete, hash:"%s", confirmations: %s, timeout: %s',
      this.pendingTransaction.hash,
      this.transactionConfirmationThreshold,
      this.transactionTimeoutSeconds
    )
    return await this.waitForTransaction(this.pendingTransaction.hash)
  }

  async start(){
    logger.debug('start');
    while(!await this.next()){
      // increasing gas price multiplier to resubmit a stuck transaction
      logger.info('Transaction timed out, increasing gas price...');
      this.currentGasPriceMultiplier *= this.gasPriceMultiplier;
      logger.info('Current gasPriceMultiplier = %s', this.currentGasPriceMultiplier);
    }
  }
}


export default IssueBatch;
