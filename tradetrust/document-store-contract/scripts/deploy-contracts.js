const DocumentStoreCreator = artifacts.require('DocumentStoreCreator');
const DocumentStore = artifacts.require('DocumentStore');
const path = require('path');
const fs = require('fs').promises;


module.exports = async function (callback){
  try{
    const BUILD_DIR = '/document-store-contract/build/contracts';
    const DOCUMENT_STORE_NAME = process.env.DOCUMENT_STORE_NAME || 'Development';
    const ADDRESSES_DIR = process.env.ADDRESSES_DIR || '/document-store-contract/addresses';
    const ABI_DIR = process.env.ABI_DIR || '/document-store-contract/abi';
    const DOCUMENT_STORE_BUILD_FILE = path.join(BUILD_DIR, 'DocumentStore.json');
    const DOCUMENT_STORE_CREATOR_BUILD_FILE = path.join(BUILD_DIR, 'DocumentStoreCreator.json');
    const DOCUMENT_STORE_ABI_FILE = path.join(ABI_DIR, 'DocumentStore.local.dev.json');
    const DOCUMENT_STORE_CREATOR_ABI_FILE = path.join(ABI_DIR, 'DocumentStoreCreator.local.dev.json');
    const DOCUMENT_STORE_ADDRESS_FILE = path.join(ADDRESSES_DIR, 'DocumentStore.local.dev.address');
    const DOCUMENT_STORE_CREATOR_ADDRESS_FILE = path.join(ADDRESSES_DIR, 'DocumentStoreCreator.local.dev.address');

    console.log('Checking DocumentStoreCreator contract');

    let documentStoreCreator, documentStore;
    try{
      documentStoreCreator = await DocumentStoreCreator.deployed();
      console.log('DocumentStoreCreator exists');
    }catch(e){
      console.log('Deploying new DocumentStoreCreator');
      documentStoreCreator = await DocumentStoreCreator.new();
    }

    console.log('Checking DocumentStoreCreator contract');
    try{
      documentStore = await DocumentStore.deployed();
      console.log('DocumentStore exists');
    }catch(e){
      console.log(`Deploying new DocumentStore('${DOCUMENT_STORE_NAME}')`);
      documentStore = await DocumentStore.new(DOCUMENT_STORE_NAME);
    }

    console.log('Saving to files');

    await fs.writeFile(DOCUMENT_STORE_ADDRESS_FILE, documentStore.address);
    console.log(`[DocumentStore address] ${documentStore.address} -> ${DOCUMENT_STORE_ADDRESS_FILE}`);
    await fs.copyFile(DOCUMENT_STORE_BUILD_FILE, DOCUMENT_STORE_ABI_FILE);
    console.log(`Copied ${DOCUMENT_STORE_BUILD_FILE} -> ${DOCUMENT_STORE_ABI_FILE}`);
    await fs.writeFile(DOCUMENT_STORE_CREATOR_ADDRESS_FILE, documentStoreCreator.address);
    console.log(`[DocumentStoreCreator address] ${documentStoreCreator.address} -> ${DOCUMENT_STORE_CREATOR_ADDRESS_FILE}`);
    await fs.copyFile(DOCUMENT_STORE_CREATOR_BUILD_FILE, DOCUMENT_STORE_CREATOR_ABI_FILE);
    console.log(`Copied ${DOCUMENT_STORE_CREATOR_BUILD_FILE} -> ${DOCUMENT_STORE_CREATOR_ABI_FILE}`);
  }catch(e){
    console.log(e);
  }


  callback();
}
