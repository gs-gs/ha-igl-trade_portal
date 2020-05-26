#!groovy

// Testing pipeline

pipeline {
    agent {
        label 'hamlet-latest'
    }
    options {
        timestamps ()
        buildDiscarder(
            logRotator(
                numToKeepStr: '10'
            )
        )
        disableConcurrentBuilds()
        durabilityHint('PERFORMANCE_OPTIMIZED')
        parallelsAlwaysFailFast()
        skipDefaultCheckout()
    }

    environment {
        DOCKER_BUILD_DIR = "${env.DOCKER_STAGE_DIR}/${BUILD_TAG}"
        PORTPREFIX = "40"
        COMPOSE_PROJECT_NAME = "trau"
    }

    parameters {
        string(
            name: 'branchref_intergov',
            defaultValue: 'master',
            description: 'The commit to use for the testing build'
        )
        booleanParam(
            name: 'run_tests',
            defaultValue: false,
            description: 'Run tests for all components'
        )
    }

    stages {
        // intergov required for running full test suite
        stage('Setup') {
            steps {
                dir("${env.DOCKER_BUILD_DIR}/test/trade_portal") {
                    script {
                        def repoTradePortalApp = checkout scm
                        env["GIT_COMMIT"] = repoTradePortalApp.GIT_COMMIT
                    }
                }
            }
        }

        stage('Testing') {

            when {
                anyOf {
                    branch 'master'
                    changeRequest()
                    equals expected: true, actual: params.run_tests
                }
            }


            stages {
                stage('Setup intergov') {

                    environment {
                        COMPOSE_PROJECT_NAME = "au"
                    }

                    steps {
                        dir("${env.DOCKER_BUILD_DIR}/test/intergov/") {
                            checkout(
                                [
                                    $class: 'GitSCM',
                                    branches: [[name: "${params.branchref_intergov}" ]],
                                    userRemoteConfigs: [[ url: 'https://github.com/trustbridge/intergov' ]]
                                ]
                            )

                            sh '''#!/bin/bash
                                touch demo-au-local.env
                                docker-compose -f demo.yml up -d
                                echo "waiting for startup"
                                sleep 15s
                            '''
                        }
                    }
                }

                stage('Setup Trade Portal') {
                    steps {
                        dir("${env.DOCKER_BUILD_DIR}/test/trade_portal/trade_portal/") {
                            sh '''#!/bin/bash
                            touch local.env
                            docker-compose -f docker-compose.yml -f demo-au.yml up -d
                            sleep 30s
                            '''
                        }
                    }
                }


                stage('Run Testing') {
                    steps {
                        dir("${env.DOCKER_BUILD_DIR}/test/trade_portal/trade_portal/") {
                            sh '''#!/bin/bash
                            docker-compose -f docker-compose.yml -f demo-au.yml run -T django py.test --junitxml=/app/tests/junit.xml
                            docker-compose -f docker-compose.yml -f demo-au.yml run -T django coverage run -m pytest
                            docker-compose -f docker-compose.yml -f demo-au.yml run -T django coverage html
                            '''
                        }
                    }

                    post {
                        always {
                            dir("${env.DOCKER_BUILD_DIR}/test/trade_portal/trade_portal/"){

                                junit 'tests/*.xml'

                                publishHTML(
                                    [
                                        allowMissing: true,
                                        alwaysLinkToLastBuild: true,
                                        keepAll: true,
                                        reportDir: 'htmlcov',
                                        reportFiles: 'index.html',
                                        reportName: 'Trade Portal Coverage Report',
                                        reportTitles: ''
                                    ]
                                )
                            }
                        }
                    }
                }
            }

            post {

                cleanup {
                    // Cleanup trade portal app
                    dir("${env.DOCKER_BUILD_DIR}/test/trade_portal/trade_portal/") {
                        sh '''#!/bin/bash
                            if [[ -f docker-compose.yml ]]; then
                                docker-compose -f docker-compose.yml -f demo-au.yml down --rmi local -v --remove-orphans
                            fi
                        '''
                    }

                    dir("${env.DOCKER_BUILD_DIR}/test/intergov/") {
                        withEnv(['COMPOSE_PROJECT_NAME=au']) {
                            sh '''#!/bin/bash
                                if [[ -f demo.yml ]]; then
                                    docker-compose -f demo.yml down --rmi local -v --remove-orphans
                                fi
                            '''
                        }
                    }
                }
            }
        }

    }

    post {
        success {
            script {
                if (env.BRANCH_NAME == 'master') {
                    build job: '../cotp-devnet/build-clients/master', parameters: [
                        string(name: 'branchref_tradeportalapp', value: "${GIT_COMMIT}")
                    ]
                }
            }
        }

        cleanup {
            cleanWs()
        }
    }
}
