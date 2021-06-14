const path = require('path');

module.exports = {
  entry: {
    'batched-issue-worker': 'src/entrypoints/batched-issue.ts',
    'batched-revoke-worker': 'src/entrypoints/batched-revoke.ts',
    'status-tracking-api': 'src/entrypoints/status-tracking-api.ts'
  },
  mode: 'production',
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
