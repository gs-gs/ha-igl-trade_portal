FROM node:alpine

WORKDIR /open-attestation-verify-api

RUN apk update && apk update && apk add bash make git python3 g++ zip

COPY package* ./
RUN npm ci
COPY ./ ./

ENTRYPOINT ./docker-entrypoint.sh
