module.exports = {
  rootDir: '.',
  moduleNameMapper:{
    'tests/(.*)': '<rootDir>/tests/$1'
  },
  preset: 'ts-jest',
  testEnvironment: 'node'
};
