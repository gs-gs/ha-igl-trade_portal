module.exports = {
  rootDir: '.',
  moduleNameMapper:{
    'src/(.*)': '<rootDir>/src/$1',
    'tests/(.*)': '<rootDir>/tests/$1'
  },
  preset: 'ts-jest',
  globals: {
    'ts-jest': {
      useESM: true,
    },
  },
  testEnvironment: 'node',
  collectCoverageFrom: [
      "src/**/*.ts",
      "!src/index.ts"
  ]
};
