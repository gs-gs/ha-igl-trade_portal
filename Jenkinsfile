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
        // Checkout the repo so we can determine change log
        skipDefaultCheckout()
    }

    parameters {
        booleanParam(
            name: 'force_deploy',
            defaultValue: false,
            description: 'Force deployment of all components'
        )
        booleanParam(
            name: 'skip_openatt_qa',
            defaultValue: false,
            description: 'Skip QA for open attestation components'
        )
    }

    environment {
        deploy_stream_job = credentials('deploy_stream_job')
        slack_channel = credentials('slack_channel')
        properties_file = credentials('properties_file')
        product_cmdb = credentials('product_cmdb')
        product_cmdb_branch = credentials('product_cmdb_branch')
    }

    stages {

        stage('Cancel running builds') {
            steps {
                milestone label: '', ordinal:  Integer.parseInt(env.BUILD_ID) - 1
                milestone label: '', ordinal:  Integer.parseInt(env.BUILD_ID)
            }
        }

        stage('Testing') {

            stages {
                stage('trade_portal') {

                    environment {
                        COMPOSE_PROJECT_NAME = "trau"
                        COMPOSE_FILE = 'docker-compose.yml'
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
                            touch devops/localdocker/local.env
                            docker-compose up --build -d

                            # run testing
                            docker-compose run -T django py.test --junitxml=/app/tests/junit.xml
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
                                junit 'tests/junit.xml'
                            }
                        }

                        cleanup {
                            // Cleanup trade portal app
                            dir('test/trade_portal/trade_portal') {
                                sh '''#!/bin/bash
                                    if [[ -f "${COMPOSE_FILE}" ]]; then
                                        docker-compose down --rmi local -v --remove-orphans
                                    fi
                                '''
                            }
                        }
                    }
                }

                stage('openatt_worker') {
                    when {
                        anyOf {
                            equals expected: false, actual: params.skip_openatt_qa
                        }
                    }

                    environment {
                        COMPOSE_FILE = 'docker-compose.yml'
                    }

                    steps {
                        dir('test/openatt_worker') {
                            checkout scm
                        }

                        dir('test/openatt_worker/tradetrust') {
                            sh '''#!/bin/bash

                            cat docker-compose.base.yml docker-compose.py-worker.yml > docker-compose.yml
                            docker-compose up --build --remove-orphans --renew-anon-volumes -d

                            # run testing
                            sleep 60s
                            docker-compose exec -T document-store-worker pytest tests -vv -x -c pytest.ini --junit-xml document-store-worker/test-report.xml
                            '''
                        }
                    }
                    post {
                        failure {
                            slackSend (
                                message: "*Warning* | <${BUILD_URL}|${JOB_NAME}> \n document-store-worker testing failed",
                                channel: "${env["slack_channel"]}",
                                color: "#f18500"
                            )
                        }

                        always {
                            dir('test/openatt_worker/tradetrust/document-store-worker'){
                                junit 'test-report.xml'
                            }
                        }

                        cleanup {
                            // Cleanup trade portal app
                            dir('test/openatt_worker/tradetrust/') {
                                sh '''#!/bin/bash
                                    if [[ -f "${COMPOSE_FILE}" ]]; then
                                        docker-compose down --rmi local -v --remove-orphans
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
                            equals expected: true, actual: params.force_deploy
                            branch 'master'
                            branch 'main'
                        }
                    }

                    environment {
                        //hamlet deployment variables
                        DEPLOYMENT_UNITS = 'www-trd,www-task-trd,www-work-trd,www-util-trd'
                        SEGMENT = 'clients'
                        BUILD_PATH = 'artefact/trade_portal/'
                        DOCKER_CONTEXT_DIR = 'artefact/trade_portal/trade_portal/'
                        BUILD_SRC_DIR = ''
                        DOCKER_FILE = 'artefact/trade_portal/trade_portal/compose/production/django/Dockerfile'
                        GENERATION_CONTEXT_DEFINED = ''

                        image_format = 'docker'
                    }

                    steps {
                        dir('.hamlet/cmdb') {
                            script {
                                git changelog: false, credentialsId: 'github', poll: false, url: "${env["product_cmdb"]}", branch: "${env["product_cmdb_branch"]}"
                                def productProperties = readProperties interpolate: true, file: "${properties_file}" ;
                                productProperties.each{ k, v -> env["${k}"] ="${v}" }

                                if( "${env["AWS_AUTOMATION_USER"]}" == "HA" ) {
                                    withCredentials([usernamePassword(credentialsId: 'aws', usernameVariable: 'aws_access_key', passwordVariable: 'aws_secret_key')]) {
                                        env["HA_AWS_ACCESS_KEY_ID"] = "${env["aws_access_key"]}"
                                        env["HA_AWS_SECRET_ACCESS_KEY"] = "${env["aws_secret_key"]}"
                                    }
                                }
                            }
                        }

                        dir('artefact/trade_portal/') {
                            script {
                                repo = checkout scm
                                env["GIT_COMMIT"] = repo.GIT_COMMIT
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
                        ${AUTOMATION_DIR}/manageImages.sh -g "${GIT_COMMIT}" -f "${image_format}"  || exit $?
                        '''

                        script {
                            def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                            contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                        }

                        build job: "${env["deploy_stream_job"]}", wait: false, parameters: [
                                extendedChoice(name: 'DEPLOYMENT_UNITS', value: "${env.DEPLOYMENT_UNITS}"),
                                string(name: 'GIT_COMMIT', value: "${env.GIT_COMMIT}"),
                                string(name: 'IMAGE_FORMATS', value: "${env.image_format}"),
                                string(name: 'SEGMENT', value: "${env["SEGMENT"]}")
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
                            equals expected: true, actual: params.force_deploy
                            branch 'master'
                            branch 'main'
                        }
                    }

                    stages{
                        stage('Setup') {
                            steps {
                                dir('artefact/tradetrust/') {
                                    script {
                                        def productProperties = readProperties interpolate: true, file: "${env.properties_file}";
                                        productProperties.each{ k, v -> env["${k}"] ="${v}" }

                                        repo = checkout scm
                                        env["GIT_COMMIT"] = repo.GIT_COMMIT
                                    }
                                }
                            }
                        }

                        stage('openatt-api') {
                            environment {
                                //hamlet deployment variables
                                DEPLOYMENT_UNITS = 'openatt-api'
                                SEGMENT = 'clients'
                                BUILD_PATH = 'artefact/tradetrust/tradetrust/open-attestation-api/'
                                BUILD_SRC_DIR = ''
                                GENERATION_CONTEXT_DEFINED = ''

                                image_format = 'openapi'
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
                                ${AUTOMATION_DIR}/manageImages.sh -g "${GIT_COMMIT}" -f "${image_format}"  || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }
                                build job: "${env["deploy_stream_job"]}", wait: false, parameters: [
                                        extendedChoice(name: 'DEPLOYMENT_UNITS', value: "${env.DEPLOYMENT_UNITS}"),
                                        string(name: 'GIT_COMMIT', value: "${env.GIT_COMMIT}"),
                                        string(name: 'IMAGE_FORMATS', value: "${env.image_format}"),
                                        string(name: 'SEGMENT', value: "${env["SEGMENT"]}")
                                ]
                            }
                        }

                        stage('openatt-api-imp') {
                            environment {
                                //hamlet deployment variables
                                DEPLOYMENT_UNITS = 'openatt-api-imp'
                                SEGMENT = 'clients'
                                BUILD_PATH = 'artefact/tradetrust/tradetrust/open-attestation-api'
                                BUILD_SRC_DIR = ''
                                GENERATION_CONTEXT_DEFINED = ''

                                image_format = 'lambda'
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
                                ${AUTOMATION_DIR}/manageImages.sh -g "${GIT_COMMIT}" -f "${image_format}"  || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }

                                build job: "${env["deploy_stream_job"]}", wait: false, parameters: [
                                        extendedChoice(name: 'DEPLOYMENT_UNITS', value: "${env.DEPLOYMENT_UNITS}"),
                                        string(name: 'GIT_COMMIT', value: "${env.GIT_COMMIT}"),
                                        string(name: 'IMAGE_FORMATS', value: "${env.image_format}"),
                                        string(name: 'SEGMENT', value: "${env["SEGMENT"]}")
                                ]
                            }
                        }

                        stage('openatt-worker') {

                            environment {
                                //hamlet deployment variables
                                DEPLOYMENT_UNITS = 'openatt-worker,openatt-contract'
                                SEGMENT = 'clients'
                                BUILD_PATH = 'artefact/tradetrust/tradetrust/document-store-worker'
                                BUILD_SRC_DIR = ''
                                DOCKER_CONTEXT_DIR = 'artefact/tradetrust/tradetrust/document-store-worker'
                                DOCKER_FILE = 'artefact/tradetrust/tradetrust/document-store-worker/Dockerfile'
                                GENERATION_CONTEXT_DEFINED = ''

                                image_format = 'docker'
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
                                ${AUTOMATION_DIR}/manageImages.sh -g "${GIT_COMMIT}" -f "${image_format}"  || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }
                                build job: "${env["deploy_stream_job"]}", wait: false, parameters: [
                                        extendedChoice(name: 'DEPLOYMENT_UNITS', value: "${env.DEPLOYMENT_UNITS}"),
                                        string(name: 'GIT_COMMIT', value: "${env.GIT_COMMIT}"),
                                        string(name: 'IMAGE_FORMATS', value: "${env.image_format}"),
                                        string(name: 'SEGMENT', value: "${env["SEGMENT"]}")
                                ]
                            }
                        }

                        stage('openatt-verify-api') {
                            environment {
                                //hamlet deployment variables
                                DEPLOYMENT_UNITS = 'openatt-verify-api'
                                SEGMENT = 'clients'
                                BUILD_PATH = 'artefact/tradetrust/tradetrust/open-attestation-verify-api'
                                BUILD_SRC_DIR = ''
                                GENERATION_CONTEXT_DEFINED = ''

                                image_format = 'openapi'

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
                                ${AUTOMATION_DIR}/manageImages.sh -g "${GIT_COMMIT}" -f "${image_format}"  || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }

                                build job: "${env["deploy_stream_job"]}", wait: false, parameters: [
                                        extendedChoice(name: 'DEPLOYMENT_UNITS', value: "${env.DEPLOYMENT_UNITS}"),
                                        string(name: 'GIT_COMMIT', value: "${env.GIT_COMMIT}"),
                                        string(name: 'IMAGE_FORMATS', value: "${env.image_format}"),
                                        string(name: 'SEGMENT', value: "${env["SEGMENT"]}")
                                ]
                            }
                        }

                        stage('openatt-verify-api-imp') {
                            environment {
                                //hamlet deployment variables
                                DEPLOYMENT_UNITS = 'openatt-verify-api-imp'
                                SEGMENT = 'clients'
                                GENERATION_CONTEXT_DEFINED = ''
                                BUILD_PATH = 'artefact/tradetrust/tradetrust/open-attestation-verify-api'
                                BUILD_SRC_DIR = ''

                                image_format = 'lambda'
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
                                ${AUTOMATION_DIR}/manageImages.sh -g "${GIT_COMMIT}" -f "${image_format}"  || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }

                                build job: "${env["deploy_stream_job"]}", wait: false, parameters: [
                                        extendedChoice(name: 'DEPLOYMENT_UNITS', value: "${env.DEPLOYMENT_UNITS}"),
                                        string(name: 'GIT_COMMIT', value: "${env.GIT_COMMIT}"),
                                        string(name: 'IMAGE_FORMATS', value: "${env.image_format}"),
                                        string(name: 'SEGMENT', value: "${env["SEGMENT"]}")
                                ]
                            }
                        }

                        stage('openatt-eth-mon') {
                            environment {
                                //hamlet deployment variables
                                DEPLOYMENT_UNITS = 'openatt-eth-mon'
                                SEGMENT = 'clients'
                                BUILD_PATH = 'artefact/tradetrust/tradetrust/monitoring'
                                BUILD_SRC_DIR = ''
                                GENERATION_CONTEXT_DEFINED = ''

                                image_format = 'lambda'
                            }

                            steps {

                                dir('artefact/tradetrust/tradetrust/monitoring') {
                                    sh '''#!/bin/bash
                                        current_py="$( pyenv global )"
                                        pyenv install 3.8.0
                                        pyenv global 3.8.0

                                        npm ci
                                        npx serverless package
                                        mkdir -p src/dist
                                        cp .serverless/tradetrust-monitoring.zip src/dist/lambda.zip

                                        pyenv global "${current_py}"
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
                                ${AUTOMATION_DIR}/manageImages.sh -g "${GIT_COMMIT}" -f "${image_format}"  || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }

                                build job: "${env["deploy_stream_job"]}", wait: false, parameters: [
                                        extendedChoice(name: 'DEPLOYMENT_UNITS', value: "${env.DEPLOYMENT_UNITS}"),
                                        string(name: 'GIT_COMMIT', value: "${env.GIT_COMMIT}"),
                                        string(name: 'IMAGE_FORMATS', value: "${env.image_format}"),
                                        string(name: 'SEGMENT', value: "${env["SEGMENT"]}")
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

                stage('plunger') {

                    when {
                        anyOf {
                            equals expected: true, actual: params.force_deploy
                            branch 'master'
                            branch 'main'
                        }
                    }

                    stages{
                        stage('Setup') {
                            steps {
                                dir('artefact/plunger/') {
                                    script {
                                        def productProperties = readProperties interpolate: true, file: "${env.properties_file}";
                                        productProperties.each{ k, v -> env["${k}"] ="${v}" }

                                        repo = checkout scm
                                        env["GIT_COMMIT"] = repo.GIT_COMMIT
                                    }
                                }
                            }
                        }

                        stage('plunger-task') {

                            environment {
                                //hamlet deployment variables
                                DEPLOYMENT_UNITS = 'openatt-plunger'
                                SEGMENT = 'clients'
                                BUILD_PATH = 'artefact/plunger/trade_portal/scripts/plunger'
                                BUILD_SRC_DIR = ''
                                DOCKER_CONTEXT_DIR = 'artefact/plunger/trade_portal/scripts/plunger'
                                DOCKER_FILE = 'artefact/plunger/trade_portal/scripts/plunger/Dockerfile'
                                GENERATION_CONTEXT_DEFINED = ''

                                image_format = 'docker'
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
                                ${AUTOMATION_DIR}/manageImages.sh -g "${GIT_COMMIT}" -f "${image_format}"  || exit $?
                                '''

                                script {
                                    def contextProperties = readProperties interpolate: true, file: "${WORKSPACE}/context.properties";
                                    contextProperties.each{ k, v -> env["${k}"] ="${v}" }
                                }
                                build job: "${env["deploy_stream_job"]}", wait: false, parameters: [
                                        extendedChoice(name: 'DEPLOYMENT_UNITS', value: "${env.DEPLOYMENT_UNITS}"),
                                        string(name: 'GIT_COMMIT', value: "${env.GIT_COMMIT}"),
                                        string(name: 'IMAGE_FORMATS', value: "${env.image_format}"),
                                        string(name: 'SEGMENT', value: "${env["SEGMENT"]}")
                                ]
                            }
                        }
                    }

                    post {
                        success {
                            slackSend (
                                message: "*Success* | <${BUILD_URL}|${JOB_NAME}> \n Plugner artefact completed",
                                channel: "${env["slack_channel"]}",
                                color: "#50C878"
                            )
                        }

                        failure {
                            slackSend (
                                message: "*Failure* | <${BUILD_URL}|${JOB_NAME}> \n Plugner artefact failed",
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
