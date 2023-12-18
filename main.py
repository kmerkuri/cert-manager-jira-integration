from kubernetes import client, config
import sys
from datetime import datetime, timedelta
from flask import Flask,request, jsonify
import jira
from jira.exceptions import JIRAError
import os
import base64
from flask_sslify import SSLify
from OpenSSL import crypto
app = Flask(__name__)
sslify = SSLify(app)
def get_secret(namespace, secret_name):
    config.load_incluster_config()

    v1 = client.CoreV1Api()

    try:
        secret = v1.read_namespaced_secret(name=secret_name, namespace=namespace)
        return secret
    except client.rest.ApiException as e:
        print(f"Error retrieving secret: {e}")
        return None
def create_jira_client():
    server = os.environ['JIRA_SERVER']
    username = os.environ['JIRA_USERNAME']
    api_token = os.environ['JIRA_API_TOKEN']

    try:
        client = jira.JIRA(server=server, basic_auth=(username, api_token))
        return client
    except JIRAError as e:
        print(f"Error occurred while connecting to JIRA: {e}")
        sys.exit(1)

def create_ticket(client, summary, description, issue_type='Task'):
    project_key = os.environ['JIRA_PROJECT_KEY']

    issue_dict = {
        'project': {'key': project_key},
        'summary': summary,
        'description': description,
        'issuetype': {'name': issue_type},
    }

    try:
        new_issue = client.create_issue(fields=issue_dict)
        return new_issue
    except JIRAError as e:
        print(f"Error occurred while creating JIRA ticket: {e}")
        sys.exit(1)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    certificate_name = data['request']['object']['metadata']['name']
    expiry_date = data['request']['object']['status']['notAfter']
    namespace = data['request']['object']['metadata']['namespace']

    secret_name = data['request']['object']['spec']['secretName']
    secret = get_secret(namespace, secret_name)
    threshold_days = 10
    if secret is not None:
        certificate = secret.data['tls.crt']
        certificate_bytes = base64.b64decode(certificate)
        x509 = crypto.load_certificate(crypto.FILETYPE_PEM, certificate_bytes)
        certificate_expiration = x509.get_notAfter().decode('utf-8')
        expiration_date = datetime.strptime(certificate_expiration, '%Y%m%d%H%M%SZ')
        threshold_date = datetime.utcnow() + timedelta(days=threshold_days)

        if expiration_date <= threshold_date:
            jira_client = create_jira_client()
            summary = f"Certificate Expiration: {certificate_name}"
            description = f"The certificate {certificate_name} will expire on {certificate_expiration}."
            create_ticket(jira_client, summary, description)

            return jsonify({"apiVersion": "admission.k8s.io/v1","kind": "AdmissionReview","response": {"uid": request.json['request']['uid'],"allowed": True}}), 200

        return jsonify({"apiVersion": "admission.k8s.io/v1","kind": "AdmissionReview","response": {"uid": request.json['request']['uid'],"allowed": True}}), 200

    return jsonify({"status": "failure", "message": "Certificate is not expired"}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080,ssl_context=('/app/certs/tls.crt', '/app/certs/tls.key'))
