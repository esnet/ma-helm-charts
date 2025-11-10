1. Enable Required APIs

```sh
gcloud services enable iamcredentials.googleapis.com --project=ma-infrastructure-474617
```

2. Create services

```sh
gcloud iam service-accounts create github-actions-helm \
  --display-name="GitHub Actions Helm Pusher" \
  --project=ma-infrastructure-474617
```

3. Grant Artifact Registry Access

```sh
gcloud artifacts repositories add-iam-policy-binding inf-helm \
  --location=us-central1 \
  --member="serviceAccount:github-actions-helm@ma-infrastructure-474617.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer" \
  --project=ma-infrastructure-474617
```

4. Create Workload Identity

```sh
gcloud iam workload-identity-pools create github-pool \
  --location="global" \
  --display-name="GitHub Actions Pool" \
  --project=ma-infrastructure-474617
 ```

5. Create Workload Identity Provider

```sh
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner == 'esnet'" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --project=ma-infrastructure-474617
```

6. Grant Service Account Access to the Pool

```sh
PROJECT_NUMBER=$(gcloud projects describe ma-infrastructure-474617 --format='value(projectNumber)')

gcloud iam service-accounts add-iam-policy-binding \
  github-actions-helm@ma-infrastructure-474617.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/esnet/ma-helm-charts" \
  --project=ma-infrastructure-474617
```

7. Get the Values for GitHub Secrets

```sh
PROJECT_NUMBER=$(gcloud projects describe ma-infrastructure-474617 --format='value(projectNumber)')
echo "WIF_PROVIDER: projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
echo "WIF_SERVICE_ACCOUNT: github-actions-helm@ma-infrastructure-474617.iam.gserviceaccount.com"
```

---

more info here: https://github.com/google-github-actions/auth#workload-identity-federation-through-a-service-account
