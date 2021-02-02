import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import { Wallet, utils, BigNumber} from 'ethers';
import { logger } from '../logger';
import { Batch } from './data';
import { Task } from './interfaces';

class IssueBatch implements Task<void>{

  private pendingTransaction: any;
  private gasPriceLimit: BigNumber;

  constructor(
    private wallet: Wallet,
    private documentStore: DocumentStore,
    private batch: Batch,
    private gasPriceMultiplier: number = 1.2,
    private transactionConfirmationThreshold: number = 12,
    private transactionTimeoutSeconds: number = 180,
    private maxAttempts: number = 10,
    private attemptsIntervalSeconds: number = 60,
    gasPriceLimitGwei: number = 200
  ){
    this.gasPriceLimit = utils.parseUnits(gasPriceLimitGwei.toString(), 'gwei');
  }

  isTransactionTimeoutError(e: any){
    logger.debug('isTransactionTimeoutError');
    return e.message.startsWith('timeout exceeded');
  }

  isHashDuplicationError(e: any){
    logger.debug('isHashDuplicationError');
    return e.message.includes('Only hashes that have not been issued can be issued');
  }

  async calculateGasPrice(gasPriceMultiplier: number): Promise<BigNumber>{
    const gasPriceWei = await this.wallet.getGasPrice();
    const gasPriceEtherMultiplied = parseFloat(utils.formatEther(gasPriceWei)) * gasPriceMultiplier;
    return utils.parseEther(gasPriceEtherMultiplied.toFixed(18));
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

  async createIssueTransaction(merkleRoot: string, gasPrice: BigNumber){
    logger.debug('createIssueTransaction');
    const transaction = await this.documentStore.populateTransaction.issue(merkleRoot);
    transaction.gasLimit = await this.wallet.estimateGas(transaction);
    transaction.gasPrice = gasPrice;
    transaction.nonce = await this.wallet.getTransactionCount('latest');
    return transaction;
  }


  async tryIssueAndWait(gasPrice: BigNumber){
    logger.debug('tryIssueAndWait');
    const merkleRoot = '0x'+this.batch.merkleRoot;
    logger.info(
      'Creating transaction for DocumentStore(%s).issue("%s")',
      this.documentStore.address,
      merkleRoot
    )
    try{
      const transaction = await this.createIssueTransaction(merkleRoot, gasPrice);
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
    return await this.waitForTransaction(this.pendingTransaction.hash);
  }



  async tryToIssueWithGasPriceAdjustment(){
    logger.debug('tryToIssueWithGasPriceAdjustment');
    let currentGasPriceMutiplier = 1;
    let currentGasPrice = await this.calculateGasPrice(currentGasPriceMutiplier);
    while(true){
      let issued = false;
      if(currentGasPrice.gte(this.gasPriceLimit)){
        logger.info(
          'Current gas price[%s gwei] >= gasLimit[%s gwei]',
          utils.formatUnits(currentGasPrice, 'gwei'),
          utils.formatUnits(this.gasPriceLimit, 'gwei')
        );
        // sending transaction without a sufficiently higher gas price will cause an error
        if(!this.pendingTransaction){
          logger.info('No transaction is sent yet, sending the first one');
          issued = await this.tryIssueAndWait(this.gasPriceLimit);
        }else{
          logger.info('Waiting for previos transaction to complete');
          issued = await this.waitForTransaction(this.pendingTransaction);
        }
      }else{
        logger.info('Sending transaction. Gas price: %s gwei', utils.formatUnits(currentGasPrice, 'gwei'));
        issued = await this.tryIssueAndWait(currentGasPrice);
      }
      if(issued){
        logger.info('Transaction confirmed');
        return true;
      }
      logger.info('Transaction time out');
      if(currentGasPrice.lt(this.gasPriceLimit)){
        currentGasPriceMutiplier *= this.gasPriceMultiplier;
        logger.info('Increasing gas price multiplier: %s', currentGasPriceMutiplier);
        currentGasPrice = await this.calculateGasPrice(currentGasPriceMutiplier);
        logger.info('Calculating new gas price: %s gwei', utils.formatUnits(currentGasPrice, 'gwei'));
      }else{
        logger.info('Gas price already reached the maximum allowed value[%s gwei], skipping gas price increase');
      }
    }
  }


  async tryToIssueRepeatedlyWithGasPriceAdjustment(){
    logger.debug('tryToIssueRepeatedlyWithGasPriceAdjustment');
      let attempt = 0;
      while(true){
        try{
          logger.info('Trying to issue the batch, attempt %s/%s', attempt + 1, this.maxAttempts);
          await this.tryToIssueWithGasPriceAdjustment();
          logger.info('The batch issued succesfully');
          this.batch.issued = true;
          return;
        }catch(e){
          logger.error('An unexpected error occured');
          logger.error(e);
          if(attempt < this.maxAttempts){
            attempt+=1;
            logger.info('Waiting %s seconds', this.attemptsIntervalSeconds);
            await new Promise(resolve=>setTimeout(resolve, this.attemptsIntervalSeconds * 1000));
          }else{
            logger.error('Ran out of attempts, issuing failed');
            this.batch.issued = false;
            return;
          }
        }
      }
  }

  async next(){
    logger.debug('next');
    return this.tryToIssueRepeatedlyWithGasPriceAdjustment();
  }

  async start(){
    logger.debug('start');
    return this.next();
  }
}


export default IssueBatch;
