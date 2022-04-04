const create = require('./app');

require('dotenv').config()
console.log(process.env) 

const app = create();
const PORT = parseInt(process.env.PORT);// || 9010;//8080;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => console.log(`Server started at ${HOST}:${PORT}`));
