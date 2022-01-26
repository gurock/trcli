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
            sh "python3 -m pytest --disable-warnings"
            }
        }
    }
}