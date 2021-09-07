const create = require('./app');

const app = create();

const PORT = process.env.PORT || 8080;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => console.log(`Server started at ${HOST}:${PORT}`));
