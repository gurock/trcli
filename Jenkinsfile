pipeline {
    agent any

    stages {
            stage('Checkout code') {
                steps {
            checkout scm
        }
    }
            stage('Install dependencies') {
                steps {
            sh "python3 -m pip install -r ./tests/requirements.txt"
        }
    }
            stage('Test') {
                steps {
                sh "python3 -m pytest --disable-warnings --alluredir=./allure-results"
                }
        }
            stage('Allure report') {
                steps {
                script {
                        allure([
                                includeProperties: false,
                                properties: [],
                                reportBuildPolicy: 'ALWAYS',
                                results: [[path: './allure-results']]
                        ])
                }
            }
        }
    }
}