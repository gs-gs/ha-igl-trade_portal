module.exports = {
  rootDir: '.',
  moduleNameMapper:{
    'src/(.*)': '<rootDir>/src/$1',
    'tests/(.*)': '<rootDir>/tests/$1'
  },
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/'
  ],
  preset: 'ts-jest',
  testEnvironment: 'node',
  collectCoverageFrom: [
      "src/**/*.ts",
      "!src/index.ts"
  ]
};
