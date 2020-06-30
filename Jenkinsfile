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
        quietPeriod 60
    }

    environment {
        DOCKER_BUILD_DIR = "${env.DOCKER_STAGE_DIR}/${BUILD_TAG}"
        COMPOSE_PROJECT_NAME = "trau"
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
            stages {
                stage('Setup Trade Portal') {
                    steps {
                        dir("${env.DOCKER_BUILD_DIR}/test/trade_portal/trade_portal/") {
                            sh '''#!/bin/bash
                            touch local.env
                            docker-compose -f docker-compose.yml up --build -d

                            # Install Node dependecices
                            npm ci
                            npm run build
                            '''
                        }
                    }
                }


                stage('Run Testing') {
                    steps {
                        dir("${env.DOCKER_BUILD_DIR}/test/trade_portal/trade_portal/") {
                            sh '''#!/bin/bash
                            docker-compose -f docker-compose.yml run -T django py.test --junitxml=/app/tests/junit.xml
                            docker-compose -f docker-compose.yml run -T django coverage run -m pytest
                            docker-compose -f docker-compose.yml run -T django coverage html
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
                                docker-compose -f docker-compose.yml down --rmi local -v --remove-orphans
                            fi
                        '''
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
                        string(name: 'branchref_tradeportal', value: "${GIT_COMMIT}")
                    ]
                }
            }
        }

        cleanup {
            cleanWs()
        }
    }
}
