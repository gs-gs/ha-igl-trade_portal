#!groovy

// Testing pipeline

pipeline {
    agent {
        label 'hamlet-latest'
    }
    options {
        buildDiscarder(
            logRotator(
                numToKeepStr: '20'
            )
        )
        skipDefaultCheckout()
    }

    parameters {
        booleanParam(
            name: 'force_trade_portal',
            defaultValue : false,
            description: 'Force deployment of trade_portal components'
        )

        booleanParam(
            name: 'force_tradetrust',
            defaultValue : false,
            description: 'Force deployment of tradetrust components'
        )
    }

    environment {
        slack_channel = "#igl-automatic-messages"
        cd_environment = "c1"
    }

    stages {
        stage('Testing') {
            stages {
                stage('trade_portal') {
                    environment {
                        COMPOSE_PROJECT_NAME = "trau"
                    }

                    steps {
                        dir('test/trade_portal') {
                            checkout scm
                        }

                        dir('test/trade_portal/trade_portal') {
                            sh '''#!/bin/bash

                            # Install Node dependecices
                            npm ci
                            npm run build

                            # build the docker service
                            touch local.env
                            docker-compose -f docker-compose.yml up --build -d

                            # run testing
                            docker-compose -f docker-compose.yml run -T django py.test --junitxml=/app/tests/junit.xml
                            docker-compose -f docker-compose.yml run -T django coverage run -m pytest
                            docker-compose -f docker-compose.yml run -T django coverage html
                            '''
                        }
                    }

                    post {
                        failure {
                            slackSend (
                                message: "*Warning* | <${BUILD_URL}|${JOB_NAME}> \n trade_portal testing failed",
                                channel: "${env["slack_channel"]}",
                                color: "#f18500"
                            )
                        }

                        always {
                            dir('test/trade_portal/trade_portal'){

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

                        cleanup {
                            // Cleanup trade portal app
                            dir('test/trade_portal/trade_portal') {
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
        }

        stage('Artefact') {
            stages{
                stage('trade_portal') {
                    when {

                        anyOf {
                            equals expected: true, actual: params.force_trade_portal
                            branch 'master'
                        }
                    }

                    environment {
                        //hamlet deployment variables
                        deployment_units = 'www-trd,www-task-trd,www-work-trd,www-util-trd'
                        segment = 'clients'
                        image_format = 'docker'
                        BUILD_PATH = 'artefact/trade_portal/'
                        DOCKER_CONTEXT_DIR = 'artefact/trade_portal/trade_portal/'
                        BUILD_SRC_DIR = 'artefact/'
                        DOCKER_FILE = 'artefact/trade_portal/trade_portal/compose/production/django/Dockerfile'
                    }

                    steps {

                        dir('artefact/trade_portal/') {
                            script {
                                repo = checkout scm
                                env["git_commit"] = repo.GIT_COMMIT
                            }
                        }

                        dir('artefact/trade_portal/trade_portal') {
                            sh '''
                                npm ci
                                npm run build
                            '''
                        }

                        uploadImageToRegistry(
                            "${env.properties_file}",
                            "${env.deployment_units.split(',')[0]}",
                            "${env.image_format}",
                            "${env.git_commit}"
                        )

                        build job: "../cote-${params["cd_environment"]}/deploy-clients", wait: false, parameters: [
                                extendedChoice(name: 'DEPLOYMENT_UNITS', value: "${env.deployment_units}"),
                                string(name: 'GIT_COMMIT', value: "${env.git_commit}"),
                                booleanParam(name: 'AUTODEPLOY', value: true),
                                string(name: 'IMAGE_FORMATS', value: "${env.image_format}"),
                        ]
                    }

                    post {
                        success {
                            slackSend (
                                message: "*Success* | <${BUILD_URL}|${JOB_NAME}> \n trade_portal artefact completed",
                                channel: "${env["slack_channel"]}",
                                color: "#50C878"
                            )
                        }

                        failure {
                            slackSend (
                                message: "*Failure* | <${BUILD_URL}|${JOB_NAME}> \n trade_portal artefact failed",
                                channel: "${env["slack_channel"]}",
                                color: "#B22222"
                            )
                        }
                    }
                }

                stage('tradetrust') {

                    when {
                        anyOf {
                            equals expected: true, actual: params.force_tradetrust
                            branch 'master'
                        }
                    }

                    stages{
                        stage('Setup') {
                            steps {
                                dir('artefact/tradetrust/') {
                                    script {
                                        repo = checkout scm
                                        env["git_commit"] = repo.GIT_COMMIT
                                    }
                                }
                            }
                        }

                        stage('openatt-api') {
                            environment {
                                //hamlet deployment variables
                                deployment_units = 'openatt-api'
                                segment = 'clients'
                                image_format = 'swagger'
                                BUILD_SRC_DIR = 'clients/'
                            }

                            steps {

                                dir('artefact/tradetrust/openatt_api/apigw') {
                                    sh '''
                                        mv "swagger.json" "swagger-extended-base.json"
                                        zip -j "swagger.zip" "swagger-extended-base.json"
                                        mkdir -p ${WORKSPACE}/clients/dist/
                                        cp "swagger.zip" ${WORKSPACE}/clients/dist/swagger.zip
                                    '''
                                }

                                uploadImageToRegistry(
                                    "${env.properties_file}",
                                    "${env.deployment_units.split(',')[0]}",
                                    "${env.image_format}",
                                    "${env.git_commit}"
                                )

                                build job: "../cote-${params["cd_environment"]}/deploy-clients", wait: false, parameters: [
                                        extendedChoice(name: 'DEPLOYMENT_UNITS', value: "${env.deployment_units}"),
                                        string(name: 'GIT_COMMIT', value: "${env.git_commit}"),
                                        booleanParam(name: 'AUTODEPLOY', value: true),
                                        string(name: 'IMAGE_FORMATS', value: "${env.image_format}"),
                                ]
                            }
                        }

                        stage('openatt-api-imp') {
                            environment {
                                //hamlet deployment variables
                                deployment_units = 'openatt-api-imp'
                                segment = 'clients'
                                image_format = 'lambda'

                                BUILD_PATH = 'ha-igl-p2/tradetrust/open-attestation-api'
                                BUILD_SRC_DIR = ''
                            }

                            steps {

                                dir('ha-igl-p2/tradetrust/open-attestation-api') {
                                    sh '''#!/bin/bash
                                        npm ci
                                        npx serverless package
                                        mkdir -p src/dist
                                        cp .serverless/openatt-api.zip src/dist/lambda.zip
                                    '''
                                }

                                uploadImageToRegistry(
                                    "${env.properties_file}",
                                    "${env.deployment_units.split(',')[0]}",
                                    "${env.image_format}",
                                    "${env.git_commit}"
                                )

                                build job: "../cote-${params["cd_environment"]}/deploy-clients", wait: false, parameters: [
                                        extendedChoice(name: 'DEPLOYMENT_UNITS', value: "${env.deployment_units}"),
                                        string(name: 'GIT_COMMIT', value: "${env.git_commit}"),
                                        booleanParam(name: 'AUTODEPLOY', value: true),
                                        string(name: 'IMAGE_FORMATS', value: "${env.image_format}"),
                                ]
                            }
                        }

                        stage('openatt-worker') {

                            environment {
                                //hamlet deployment variables
                                deployment_units = 'openatt-worker,openatt-contract'
                                segment = 'channel'
                                image_format = 'docker'
                                BUILD_PATH = 'ha-igl-p2/tradetrust/document-store-worker'
                                DOCKER_CONTEXT_DIR = 'ha-igl-p2/tradetrust/document-store-worker'
                                BUILD_SRC_DIR = ''
                                DOCKER_FILE = 'ha-igl-p2/tradetrust/document-store-worker/Dockerfile'
                            }

                            steps {

                                uploadImageToRegistry(
                                    "${env.properties_file}",
                                    "${env.deployment_units.split(',')[0]}",
                                    "${env.image_format}",
                                    "${env.git_commit}"
                                )

                                build job: "../cote-${params["cd_environment"]}/deploy-clients", wait: false, parameters: [
                                        extendedChoice(name: 'DEPLOYMENT_UNITS', value: "${env.deployment_units}"),
                                        string(name: 'GIT_COMMIT', value: "${env.git_commit}"),
                                        booleanParam(name: 'AUTODEPLOY', value: true),
                                        string(name: 'IMAGE_FORMATS', value: "${env.image_format}"),
                                ]
                            }
                        }

                        stage('openatt-verify-api') {
                            environment {
                                //hamlet deployment variables
                                deployment_units = 'openatt-verify-api'
                                segment = 'clients'
                                image_format = 'swagger'

                                BUILD_PATH = 'ha-igl-p2/tradetrust/open-attestation-verify-api'
                                BUILD_SRC_DIR = ''
                            }

                            steps {

                                dir('ha-igl-p2/tradetrust/open-attestation-verify-api') {
                                    sh '''
                                        npm ci
                                        npm run bundle-api-specs
                                        npx swagger-cli bundle -t json -o swagger-extended-base.json api.yml

                                        zip -j "swagger.zip" "swagger-extended-base.json"
                                        mkdir -p src/dist/
                                        cp "swagger.zip" src/dist/swagger.zip
                                    '''
                                }

                                uploadImageToRegistry(
                                    "${env.properties_file}",
                                    "${env.deployment_units.split(',')[0]}",
                                    "${env.image_format}",
                                    "${env.git_commit}"
                                )

                                build job: "../cote-${params["cd_environment"]}/deploy-clients", wait: false, parameters: [
                                        extendedChoice(name: 'DEPLOYMENT_UNITS', value: "${env.deployment_units}"),
                                        string(name: 'GIT_COMMIT', value: "${env.git_commit}"),
                                        booleanParam(name: 'AUTODEPLOY', value: true),
                                        string(name: 'IMAGE_FORMATS', value: "${env.image_format}"),
                                ]
                            }
                        }

                        stage('openatt-verify-api-imp') {
                            environment {
                                //hamlet deployment variables
                                deployment_units = 'openatt-verify-api-imp'
                                segment = 'clients'
                                image_format = 'lambda'

                                BUILD_PATH = 'ha-igl-p2/tradetrust/open-attestation-verify-api'
                                BUILD_SRC_DIR = ''
                            }

                            steps {

                                dir('ha-igl-p2/tradetrust/open-attestation-verify-api') {
                                    sh '''#!/bin/bash
                                        npm ci
                                        npx serverless package
                                        mkdir -p src/dist
                                        cp .serverless/open-attestation-verify-api.zip src/dist/lambda.zip
                                    '''
                                }

                                uploadImageToRegistry(
                                    "${env.properties_file}",
                                    "${env.deployment_units.split(',')[0]}",
                                    "${env.image_format}",
                                    "${env.git_commit}"
                                )

                                build job: "../cote-${params["cd_environment"]}/deploy-clients", wait: false, parameters: [
                                        extendedChoice(name: 'DEPLOYMENT_UNITS', value: "${env.deployment_units}"),
                                        string(name: 'GIT_COMMIT', value: "${env.git_commit}"),
                                        booleanParam(name: 'AUTODEPLOY', value: true),
                                        string(name: 'IMAGE_FORMATS', value: "${env.image_format}"),
                                ]
                            }
                        }
                    }

                    post {
                        success {
                            slackSend (
                                message: "*Success* | <${BUILD_URL}|${JOB_NAME}> \n Tradetrust artefact completed",
                                channel: "${env["slack_channel"]}",
                                color: "#50C878"
                            )
                        }

                        failure {
                            slackSend (
                                message: "*Failure* | <${BUILD_URL}|${JOB_NAME}> \n Tradetrust artefact failed",
                                channel: "${env["slack_channel"]}",
                                color: "#B22222"
                            )
                        }
                    }
                }
            }
        }
    }
}
