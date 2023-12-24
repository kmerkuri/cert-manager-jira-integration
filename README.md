### Cert manager integration with Jira automatic issue creation when certificate is about to expire

# Deploy cert-manager using helm

```shell
helm install \
  cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.3 \
  --set installCRDs=true
  --set prometheus.enabled=false \  # Example: disabling prometheus using a Helm parameter
  --set webhook.timeoutSeconds=4   # Example: changing the webhook timeout using a Helm parameter

```
- Note : Dont forget to set up Issuers or Cluster issuers

# Build the image and push it into your docker registry

```docker
docker build -t <name of registry>/<image name>:<image tag> .
docker push <name of registry>/<image name>:<image tag>
```

# Create a your certificate and a kubernetes secret out of that certificate

```shell
Example with a certifcate that expires in two days
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 2
kubectl create secret tls <secret name> --key="cert.pem" --cert="key.pem" -n <namespace>
```
# Make changes to the deployment yaml
```shell
- Edit the k8s/deployment.yaml and set image: <name of registry>/<image name>:<image tag> , set env JIRA_SERVER,JIRA_USERNAME,JIRA_API_TOKEN,JIRA_PROJECT_KEY
  and secretName: <name of the secret tks you created earlier>
```
# Make changes to the MutatingWebhookConfiguration

- Get the ca.crt data from the certificate tls you created earlier and replace caBundle: in the mutation.yaml

# Finishing off

- Apply everything in the k8s folder after changes
```shell
kubectl apply -f k8s/
```
