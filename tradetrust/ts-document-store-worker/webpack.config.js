const path = require('path');

module.exports = {
  entry: {
    '2.0/batched-issue-worker': 'src/entrypoints/2.0/batched-issue.ts',
    '2.0/batched-revoke-worker': 'src/entrypoints/2.0/batched-revoke.ts',
    '3.0/batched-issue-worker': 'src/entrypoints/3.0/batched-issue.ts',
    '3.0/batched-revoke-worker': 'src/entrypoints/3.0/batched-revoke.ts'
  },
  mode: 'production',
  devtool: 'source-map',
  target: 'node',
  module: {
    rules: [
      {
        test: /\.ts$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
    ],
  },
  resolve: {
    extensions: [ '.tsx', '.ts', '.js' ],
    alias: {
      'src': path.resolve(__dirname, 'src'),
      'tests': path.resolve(__dirname, 'tests')
    }
  },
  output: {
    filename: 'bundle/[name].js',
    path: path.resolve(__dirname, 'dist'),
  },
};
