#!/usr/bin/env bash
# One-shot deploy from a developer laptop. Requires gcloud + docker.
#
# Usage:
#   PROJECT_ID=rotune-493315 REGION=us-central1 ./infra/deploy.sh
#
# What it does:
#   1. Ensures the Artifact Registry repo exists (priorauth)
#   2. Submits a Cloud Build using infra/cloudbuild.yaml which builds, pushes,
#      and deploys both services
#
# Secrets ANTHROPIC_API_KEY and OPENROUTER_API_KEY must already exist in
# Secret Manager. Create them once with:
#
#   echo -n "$KEY" | gcloud secrets create OPENROUTER_API_KEY --data-file=-

set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
: "${REGION:=us-central1}"
REPO="${REPO:-priorauth}"

cd "$(dirname "$0")/.."

if ! gcloud artifacts repositories describe "$REPO" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "Creating Artifact Registry repo $REPO in $REGION"
    gcloud artifacts repositories create "$REPO" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Prior Authorization Agent images" \
        --project="$PROJECT_ID"
fi

gcloud builds submit \
    --config infra/cloudbuild.yaml \
    --substitutions=_REGION="$REGION",_REPO="$REPO" \
    --project="$PROJECT_ID" \
    .

echo
echo "Deploy complete. Service URLs:"
gcloud run services list --platform=managed --region="$REGION" --project="$PROJECT_ID" --filter="metadata.name:priorauth-*" \
    --format="table(metadata.name,status.url)"
