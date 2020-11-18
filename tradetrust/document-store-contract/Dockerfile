FROM node:12-alpine


WORKDIR /document-store-contract

ARG DOCUMENT_STORE_MASTER_COMMIT

RUN apk update && apk add --no-cache git bash make gcc g++ python3 python3-dev

RUN git init \
  && git remote add upstream https://github.com/Open-Attestation/document-store.git \
  && git fetch upstream master \
  && git merge ${DOCUMENT_STORE_MASTER_COMMIT}

# sha3 in package json is broken apparently, so I upgrade it manually.
RUN npm install --save sha3 && npm install

RUN npm run truffle -- build

COPY scripts/* /document-store-contract/

ENTRYPOINT /document-store-contract/docker-entrypoint.sh
