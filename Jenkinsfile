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

                            echo "TODO: run unit tests"
                            '''
                        }
                    }
                    post {
                        failure {
                            slackSend (
                                message: "*Warning* | <${BUILD_URL}|${JOB_NAME}> \n ts-document-store-worker testing failed",
                                channel: "${env["slack_channel"]}",
                                color: "#f18500"
                            )
                        }

                        // always {
                        //     dir('test/openatt_worker/tradetrust/ts-document-store-worker'){
                        //         junit 'test-report.xml'
                        //     }
                        // }

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

            post {
                cleanup {
                    cleanWs()
                }
            }
        }

        stage('deploy') {

            environment {
                ROOT_DIR = "${WORKSPACE}/cmdb"
                SEGMENT = 'clients'
            }

            stages{

                stage ('setup') {
                    steps {
                        withFolderProperties {
                            dir('cmdb/') {
                                git(
                                    credentialsId: 'github',
                                    changelog: false,
                                    poll: false,
                                    url: env.product_cmdb_url,
                                    branch: env.product_cmdb_branch
                                )
                            }

                            dir('code/') {
                                script {
                                    repo = checkout scm
                                    env["GIT_COMMIT"] = repo.GIT_COMMIT
                                }
                            }

                            sh '''
                                pip install -q --upgrade hamlet
                                hamlet engine install-engine --update tram
                                hamlet engine set-engine tram
                            '''

                            // Make folder properties available for rest of deploy jobs
                            withFolderProperties{
                                script {
                                    env['TENANT'] = env.TENANT
                                    env['PRODUCT'] = env.PRODUCT
                                    env['ACCOUNT'] = env.ACCOUNT
                                    env['ENVIRONMENT'] = env.ENVIRONMENT

                                    env['HAMLET_AWS_AUTH_SOURCE'] = env.HAMLET_AWS_AUTH_SOURCE
                                    env['HAMLET_AWS_AUTH_USER'] = env.HAMLET_AWS_AUTH_USER

                                    env['slack_channel'] = env.slack_channel

                                    env['product_cmdb_branch'] = env.product_cmdb_branch
                                    env['product_cmdb_url'] = env.product_cmdb_url
                                    env['account_cmdb_branch'] = env.account_cmdb_branch
                                    env['account_cmdb_url'] = env.account_cmdb_url
                                }
                            }
                        }
                    }

                }

                stage('trade_portal') {
                    when {
                        anyOf {
                            equals expected: true, actual: params.force_deploy
                            allOf {
                                anyOf {
                                    branch 'master'
                                    branch 'main'
                                    branch 'cd_*'
                                }
                                anyOf {
                                    changeset '*/trade_portal/**'
                                    changeset '*/Jenkinsfile'
                                }
                            }
                        }
                    }

                    steps {
                        dir('code/trade_portal') {
                            sh '''#!/bin/bash
                                npm ci
                                npm run build
                            '''


                            sh '''#!/bin/bash
                                hamlet release upload-image -u www-trd -f docker -r "${GIT_COMMIT}" \
                                    --dockerfile compose/production/django/Dockerfile --docker-context .

                                hamlet release update-image-reference -u www-trd -f docker -r "${GIT_COMMIT}"
                            '''

                            sh '''#!/bin/bash
                                # Running migration before deploy
                                hamlet deploy run-deployments -u www-task-trd
                                hamlet run task -t application -i app-ecs \
                                        -w www-task -x trade -y "" -c www \
                                        -e APP_TASK_LIST -v "migrate --no-input"

                                # Running deploy of other units
                                hamlet deploy run-deployments -u www-trd -u www-work-trd -u www-util-trd
                            '''
                        }
                    }

                    post {
                        success {
                            slackSend (
                                message: "*Success* | <${BUILD_URL}|${JOB_NAME}> \n trade_portal deployment completed",
                                channel: env.slack_channel,
                                color: "#50C878"
                            )
                        }

                        failure {
                            slackSend (
                                message: "*Failure* | <${BUILD_URL}|${JOB_NAME}> \n trade_portal deployment completed",
                                channel: env.slack_channel,
                                color: "#B22222"
                            )
                        }
                    }
                }

                stage('tradetrust') {

                    when {
                        anyOf {
                            equals expected: true, actual: params.force_deploy
                            allOf {
                                anyOf {
                                    branch 'master'
                                    branch 'main'
                                    branch 'cd_*'
                                }
                                anyOf {
                                    changeset 'tradetrust/**'
                                    changeset 'Jenkinsfile'
                                }
                            }
                        }
                    }

                    stages{
                        stage('openatt-api') {
                            steps {
                                dir('code/tradetrust/open-attestation-api/') {
                                    sh '''
                                        npx swagger-cli bundle --dereference --outfile build/openapi-extended-base.json --type json api.yml
                                        npx swagger-cli validate build/openapi-extended-base.json
                                    '''

                                    sh '''
                                        hamlet release upload-image -u openatt-api -f openapi -r "${GIT_COMMIT}" \
                                            --image-path build/

                                        hamlet release update-image-reference -u openatt-api -f openapi -r "${GIT_COMMIT}"
                                    '''

                                    sh '''
                                        hamlet deploy run-deployments -u openatt-api
                                    '''
                                }
                            }
                        }

                        stage('openatt-api-imp') {
                            steps {

                                dir('code/tradetrust/open-attestation-api') {
                                    sh '''#!/bin/bash
                                        npm ci
                                        npx serverless package
                                    '''

                                    sh '''#!/bin/bash
                                        hamlet release upload-image -u openatt-api-imp -f lambda \
                                            -r "${GIT_COMMIT}" --image-path .serverless/openatt-api.zip

                                        hamlet release update-image-reference -u openatt-api-imp -f lambda \
                                            -r "${GIT_COMMIT}"
                                    '''

                                    sh '''#!/bin/bash
                                        hamlet deploy run-deployments -u openatt-api-imp
                                    '''

                                }
                            }
                        }

                        stage('openatt-worker') {
                            steps {

                                dir('code/tradetrust/ts-document-store-worker') {
                                    sh '''#!/bin/bash
                                        hamlet release upload-image -u openatt-worker -f docker \
                                            -r "${GIT_COMMIT}" --dockerfile Dockerfile --docker-context .

                                        hamlet release update-image-reference -u openatt-worker -f docker \
                                            -r "${GIT_COMMIT}"
                                    '''

                                    sh '''#!/bin/bash
                                        hamlet deploy run-deployments -u openatt-worker -u openatt-contract
                                    '''
                                }
                            }
                        }

                        stage('openatt-verify-api') {
                            steps {

                                dir('code/tradetrust/open-attestation-verify-api') {
                                    sh '''
                                        npx swagger-cli bundle -t json -o build/openapi-extended-base.json api.yml
                                        npx swagger-cli validate build/openapi-extended-base.json
                                    '''

                                    sh '''
                                        hamlet release upload-image -u openatt-verify-api -f openapi -r "${GIT_COMMIT}" \
                                            --image-path build/

                                        hamlet release update-image-reference -u openatt-verify-api -f openapi -r "${GIT_COMMIT}"
                                    '''

                                    sh '''
                                        hamlet deploy run-deployments -u openatt-verify-api
                                    '''
                                }
                            }
                        }

                        stage('openatt-verify-api-imp') {
                            steps {

                                dir('code/tradetrust/open-attestation-verify-api') {
                                    sh '''#!/bin/bash
                                        npm ci
                                        npx serverless package
                                    '''

                                    sh '''#!/bin/bash
                                        hamlet release upload-image -u openatt-verify-api-imp -f lambda \
                                            -r "${GIT_COMMIT}" --image-path .serverless/open-attestation-verify-api.zip

                                        hamlet release update-image-reference -u openatt-verify-api-imp -f lambda \
                                            -r "${GIT_COMMIT}"
                                    '''

                                    sh '''#!/bin/bash
                                        hamlet deploy run-deployments -u openatt-verify-api-imp
                                    '''
                                }
                            }
                        }

                        stage('openatt-eth-mon') {
                            steps {

                                dir('code/tradetrust/monitoring') {
                                    sh '''#!/bin/bash
                                        current_py="$( pyenv global )"
                                        pyenv install 3.8.0
                                        pyenv global 3.8.0

                                        npm ci
                                        npx serverless package

                                        pyenv global "${current_py}"
                                    '''

                                    sh '''#!/bin/bash
                                        hamlet release upload-image -u openatt-eth-mon -f lambda \
                                            -r "${GIT_COMMIT}" --image-path .serverless/tradetrust-monitoring.zip

                                        hamlet release update-image-reference -u openatt-eth-mon -f lambda \
                                            -r "${GIT_COMMIT}"
                                    '''

                                    sh '''#!/bin/bash
                                        hamlet deploy run-deployments -u openatt-eth-mon
                                    '''
                                }
                            }
                        }
                    }

                    post {
                        success {
                            slackSend (
                                message: "*Success* | <${BUILD_URL}|${JOB_NAME}> \n Tradetrust deployment completed",
                                channel: "${env["slack_channel"]}",
                                color: "#50C878"
                            )
                        }

                        failure {
                            slackSend (
                                message: "*Failure* | <${BUILD_URL}|${JOB_NAME}> \n Tradetrust deployment failed",
                                channel: "${env["slack_channel"]}",
                                color: "#B22222"
                            )
                        }
                    }
                }
            }

            post {
                always {
                    withCredentials([gitUsernamePassword(credentialsId: 'github')]) {
                        sh '''
                            git config --global user.name "JenkinsPipeline"
                            git config --global user.email "${CHANGE_AUTHOR_EMAIL:-Jenkins@pipeline.local}"

                            hamlet cmdb commit-changes --products --commit-message "${BUILD_TAG}" --branch "${product_cmdb_branch}"
                        '''
                    }
                }
            }
        }
    }
}
