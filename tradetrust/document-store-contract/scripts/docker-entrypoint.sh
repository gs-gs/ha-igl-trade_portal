echo "Document store contract container started"
npm run truffle -- exec deploy-contracts.js
echo "Waiting forever..."
tail -f /dev/null
