import app from './app';

const instance = app();

const PORT = parseInt(`${process.env.PORT || 8080}`);
const HOST = '0.0.0.0';

instance.listen(PORT, HOST, () => console.log(`Server started at ${HOST}:${PORT}`));
