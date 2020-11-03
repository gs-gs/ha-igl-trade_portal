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
        properties_file = "/var/opt/properties/devnet.properties"
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

                        sh '''#!/bin/bash
                        ${AUTOMATION_BASE_DIR}/setContext.sh || exit $?
                        '''

                        script {
                            def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                            contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                        }

                        sh '''#!/bin/bash
                        ${AUTOMATION_DIR}/manageImages.sh -g "${git_commit}" -u "${deployment_units}" -f "${image_format}"  || exit $?
                        '''

                        script {
                            def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                            contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                        }

                        build job: "../../deploy/deploy-${env["cd_environment"]}-clients", wait: false, parameters: [
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
                                BUILD_SRC_DIR = 'artefact/tradetrust/tradetrust/open-attestation-api/'
                            }

                            steps {

                                dir('artefact/tradetrust/tradetrust/open-attestation-api/') {
                                    sh '''
                                    npm install swagger-cli --no-save
                                    npx swagger-cli bundle --dereference --outfile openapi-extended-base.json --type json api.yml
                                    npx swagger-cli validate openapi-extended-base.json

                                    zip -j "openapi.zip" "openapi-extended-base.json"
                                    mkdir -p src/dist/
                                    cp "openapi.zip" src/dist/openapi.zip
                                    '''
                                }
                                sh '''#!/bin/bash
                                ${AUTOMATION_BASE_DIR}/setContext.sh || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }

                                sh '''#!/bin/bash
                                ${AUTOMATION_DIR}/manageImages.sh -g "${git_commit}" -u "${deployment_units}" -f "${image_format}"  || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }
                                build job: "../../deploy/deploy-${env["cd_environment"]}-clients", wait: false, parameters: [
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

                                BUILD_PATH = 'artefact/tradetrust/tradetrust/open-attestation-api'
                                BUILD_SRC_DIR = ''
                            }

                            steps {

                                dir('artefact/tradetrust/tradetrust/open-attestation-api') {
                                    sh '''#!/bin/bash
                                        npm ci
                                        npx serverless package
                                        mkdir -p src/dist
                                        cp .serverless/openatt-api.zip src/dist/lambda.zip
                                    '''
                                }

                                sh '''#!/bin/bash
                                ${AUTOMATION_BASE_DIR}/setContext.sh || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }

                                sh '''#!/bin/bash
                                ${AUTOMATION_DIR}/manageImages.sh -g "${git_commit}" -u "${deployment_units}" -f "${image_format}"  || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }

                                build job: "../../deploy/deploy-${env["cd_environment"]}-clients", wait: false, parameters: [
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
                                BUILD_PATH = 'artefact/tradetrust/tradetrust/document-store-worker'
                                DOCKER_CONTEXT_DIR = 'artefact/tradetrust/tradetrust/document-store-worker'
                                BUILD_SRC_DIR = ''
                                DOCKER_FILE = 'artefact/tradetrust/tradetrust/document-store-worker/Dockerfile'
                            }

                            steps {

                                sh '''#!/bin/bash
                                ${AUTOMATION_BASE_DIR}/setContext.sh || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }

                                sh '''#!/bin/bash
                                ${AUTOMATION_DIR}/manageImages.sh -g "${git_commit}" -u "${deployment_units}" -f "${image_format}"  || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }
                                build job: "../../deploy/deploy-${env["cd_environment"]}-clients", wait: false, parameters: [
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

                                BUILD_PATH = 'artefact/tradetrust/tradetrust/open-attestation-verify-api'
                                BUILD_SRC_DIR = ''
                            }

                            steps {

                                dir('artefact/tradetrust/tradetrust/open-attestation-verify-api') {
                                    sh '''
                                        npm ci
                                        npx swagger-cli bundle -t json -o openapi-extended-base.json api.yml

                                        zip -j "openapi.zip" "openapi-extended-base.json"
                                        mkdir -p src/dist/
                                        cp "openapi.zip" src/dist/openapi.zip
                                    '''
                                }

                                sh '''#!/bin/bash
                                ${AUTOMATION_BASE_DIR}/setContext.sh || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }

                                sh '''#!/bin/bash
                                ${AUTOMATION_DIR}/manageImages.sh -g "${git_commit}" -u "${deployment_units}" -f "${image_format}"  || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }

                                build job: "../../deploy/deploy-${env["cd_environment"]}-clients", wait: false, parameters: [
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

                                BUILD_PATH = 'artefact/tradetrust/tradetrust/open-attestation-verify-api'
                                BUILD_SRC_DIR = ''
                            }

                            steps {

                                dir('artefact/tradetrust/tradetrust/open-attestation-verify-api') {
                                    sh '''#!/bin/bash
                                        npm ci
                                        npx serverless package
                                        mkdir -p src/dist
                                        cp .serverless/open-attestation-verify-api.zip src/dist/lambda.zip
                                    '''
                                }

                                sh '''#!/bin/bash
                                ${AUTOMATION_BASE_DIR}/setContext.sh || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }

                                sh '''#!/bin/bash
                                ${AUTOMATION_DIR}/manageImages.sh -g "${unit_git_commit}" -u "${deployment_unit}" -f "${image_format}"  || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }

                                build job: "../../deploy/deploy-${env["cd_environment"]}-clients", wait: false, parameters: [
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
