module.exports = {
  rootDir: '.',
  moduleNameMapper:{
    'src/(.*)': '<rootDir>/src/$1',
    'tests/(.*)': '<rootDir>/tests/$1'
  },
  preset: 'ts-jest',
  testEnvironment: 'node',
};
