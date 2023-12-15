
import os
import sys
import json
from datetime import datetime, timedelta
from flask import Flask, request
import jira
from jira.exceptions import JIRAError
app = Flask(__name__)

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
    payload = request.get_json()

    # Get the certificate expiration date from the payload
    expiration_date = datetime.strptime(payload['certificate']['notAfter'], '%Y-%m-%dT%H:%M:%SZ')

    # Compare the expiration date with the current date
    now = datetime.now()
    expiration_threshold = timedelta(days=os.environ['CERTIFICATE_EXPIRATION_THRESHOLD'])
    is_certificate_expiring = (expiration_date - now) <= expiration_threshold

    if is_certificate_expiring:
        jira_client = create_jira_client()
        summary = f"Certificate Expiration: {payload['certificate']['commonName']}"
        description = f"The certificate {payload['certificate']['commonName']} will expire on 
{expiration_date.strftime('%Y-%m-%d')}."
        create_ticket(jira_client, summary, description)

    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

