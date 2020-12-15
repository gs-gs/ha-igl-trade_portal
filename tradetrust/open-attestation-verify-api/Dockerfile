FROM node:14-alpine

WORKDIR /open-attestation-verify-api

RUN apk update && apk update && apk add bash make git python3 g++ zip && chmod 777 /open-attestation-verify-api

USER node

COPY package* ./
RUN npm ci
COPY ./ ./

ENTRYPOINT ./docker-entrypoint.sh
