import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import { Wallet, utils, BigNumber} from 'ethers';
import { logger } from '../logger';
import { Batch } from './data';
import { Task } from './interfaces';

class IssueBatch implements Task<void>{

  private pendingTransaction: any;
  private gasPriceLimit: BigNumber;
  private currentGasPriceMutiplier!: number;
  private currentGasPrice!: BigNumber;
  private lastGasPrice!: BigNumber;
  private wallet: Wallet;
  private documentStore: DocumentStore;
  private batch: Batch;
  private transactionConfirmationThreshold: number;
  private transactionTimeoutSeconds: number;
  private attempts: any;
  private attemptsIntervalSeconds: number;
  private gasPriceMultiplier: number;

  constructor({
    wallet,
    documentStore,
    batch,
    gasPriceMultiplier = 1.2,
    gasPriceLimitGwei = 200,
    transactionConfirmationThreshold = 12,
    transactionTimeoutSeconds = 180,
    attempts = 10,
    attemptsIntervalSeconds = 60,
  }:{
    wallet: Wallet,
    documentStore: DocumentStore,
    batch: Batch
    gasPriceMultiplier?: number,
    gasPriceLimitGwei?: number,
    transactionConfirmationThreshold?: number,
    transactionTimeoutSeconds?: number,
    attempts?: number,
    attemptsIntervalSeconds?: number,
  }){
    this.wallet = wallet;
    this.documentStore = documentStore;
    this.batch = batch;
    this.gasPriceMultiplier = gasPriceMultiplier;
    this.transactionConfirmationThreshold = transactionConfirmationThreshold;
    this.transactionTimeoutSeconds = transactionTimeoutSeconds;
    this.attempts = attempts;
    this.attemptsIntervalSeconds = attemptsIntervalSeconds;
    this.gasPriceLimit = utils.parseUnits(gasPriceLimitGwei.toString(), 'gwei');
  }

  isTransactionTimeoutError(e: any){
    logger.debug('isTransactionTimeoutError');
    return e.message.includes('timeout exceeded');
  }

  isHashDuplicationError(e: any){
    logger.debug('isHashDuplicationError');
    return e.message.includes('Only hashes that have not been issued can be issued');
  }

  isUnderpricedTransactionError(e: any){
    logger.debug('isUnderpricedTransactionError');
    return e.message.includes('replacement transaction underpriced');
  }

  async calculateGasPrice(gasPriceMultiplier: number): Promise<BigNumber>{
    const gasPriceWei = await this.wallet.getGasPrice();
    const gasPriceEtherMultiplied = parseFloat(utils.formatEther(gasPriceWei)) * gasPriceMultiplier;
    return utils.parseEther(gasPriceEtherMultiplied.toFixed(18));
  }


  async waitForTransaction(hash: string): Promise<boolean>{
    logger.debug('waitForTransaction');
    logger.info(
      'Waiting for transaction to complete, hash:"%s", confirmations: %s, timeout: %s',
      hash,
      this.transactionConfirmationThreshold,
      this.transactionTimeoutSeconds
    )
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
      } else if(this.isUnderpricedTransactionError(e)){
        logger.info('Underpriced transaction error received, ignoring the transaction');
        return false;
      }
      else{
        throw e;
      }
    }
    return await this.waitForTransaction(this.pendingTransaction.hash);
  }



  async tryToIssueWithGasPriceAdjustment(){
    logger.debug('tryToIssueWithGasPriceAdjustment');
    // these values are in the state to restore after a critical failure
    this.currentGasPriceMutiplier = this.currentGasPriceMutiplier??1;
    this.currentGasPrice = this.currentGasPrice??(await this.calculateGasPrice(this.currentGasPriceMutiplier));
    this.lastGasPrice = this.lastGasPrice??this.currentGasPrice;
    logger.info('Current gas price multiplier %s', this.currentGasPriceMutiplier);
    logger.info('Current gas price %s gwei', utils.formatUnits(this.currentGasPrice, 'gwei'));
    logger.info('Last gas price %s gwei', utils.formatUnits(this.lastGasPrice, 'gwei'));
    while(true){
      let issued = false;
      if(this.currentGasPrice.gte(this.gasPriceLimit)){
        logger.info(
          'Current gas price[%s gwei] >= gasLimit[%s gwei]',
          utils.formatUnits(this.currentGasPrice, 'gwei'),
          utils.formatUnits(this.gasPriceLimit, 'gwei')
        );
        // sending transaction without a sufficiently higher gas price will cause an error
        if(!this.pendingTransaction || this.lastGasPrice.lt(this.gasPriceLimit)){
          logger.info(
            'No transaction is sent yet, or last gas price[%s gwei] < gas price limit[%s gwei]',
            utils.formatUnits(this.lastGasPrice, 'gwei'),
            utils.formatUnits(this.gasPriceLimit, 'gwei')
          );
          issued = await this.tryIssueAndWait(this.gasPriceLimit);
          // to prevent further occurences of UnderpricedTransactionError
          this.lastGasPrice = this.gasPriceLimit;
        }else{
          issued = await this.waitForTransaction(this.pendingTransaction.hash);
        }
      }else{
        logger.info('Sending transaction. Gas price: %s gwei', utils.formatUnits(this.currentGasPrice, 'gwei'));
        issued = await this.tryIssueAndWait(this.currentGasPrice);
      }
      if(issued){
        logger.info('Transaction confirmed');
        return true;
      }
      logger.info('Transaction time out');
      if(this.currentGasPrice.lt(this.gasPriceLimit)){
        this.lastGasPrice = this.currentGasPrice;
        this.currentGasPriceMutiplier *= this.gasPriceMultiplier;
        logger.info('Increasing gas price multiplier: %s', this.currentGasPriceMutiplier);
        this.currentGasPrice = await this.calculateGasPrice(this.currentGasPriceMutiplier);
        logger.info('Calculating new gas price: %s gwei', utils.formatUnits(this.currentGasPrice, 'gwei'));
      }else{
        logger.info(
          'Gas price already reached the maximum allowed value[%s/%s gwei], skipping gas price increase',
          utils.formatUnits(this.currentGasPrice, 'gwei'),
          utils.formatUnits(this.gasPriceLimit, 'gwei')
        );
      }
    }
  }


  async tryToIssueRepeatedlyWithGasPriceAdjustment(){
    logger.debug('tryToIssueRepeatedlyWithGasPriceAdjustment');
    let attempt = 0;
    while(true){
      try{
        logger.info('Trying to issue the batch, attempt %s/%s', attempt + 1, this.attempts);
        await this.tryToIssueWithGasPriceAdjustment();
        logger.info('The batch issued succesfully');
        this.batch.issued = true;
        return;
      }catch(e){
        // if process fails during gas price increase it can still pick up using this.pendingTransaction property
        logger.error('An unexpected error occured');
        logger.error(e);
        attempt+=1;
        if(attempt < this.attempts){
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
