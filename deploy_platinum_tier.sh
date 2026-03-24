#!/bin/bash
# Platinum Tier Deployment Script

echo "AI Employee Platinum Tier Deployment Script"
echo "==========================================="

# Check if required tools are installed
echo "Checking required tools..."

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "Error: git is not installed"
    exit 1
fi

if ! python3 -c "import git" &> /dev/null; then
    echo "Installing GitPython..."
    pip3 install GitPython
fi

echo "All required tools are available."

# Create vault structure if it doesn't exist
echo "Setting up vault structure..."
mkdir -p vault/Needs_Action/{email,social,odoo,payment,whatsapp}
mkdir -p vault/Plans/{email,social,odoo,payment,whatsapp}
mkdir -p vault/Pending_Approval/{email,social,odoo,payment,whatsapp}
mkdir -p vault/In_Progress/{cloud_exec,local_exec}
mkdir -p vault/{Updates,Signals,Drafts,Archive,Done,Approved,Rejected,Logs}

echo "Vault structure created."

# Initialize git repo in vault if it doesn't exist
if [ ! -d "vault/.git" ]; then
    echo "Initializing vault as git repository..."
    cd vault
    git init
    echo ".env" >> .gitignore
    echo "tokens.json" >> .gitignore
    echo "credentials.json" >> .gitignore
    echo "whatsapp_session*" >> .gitignore
    echo "banking_creds*" >> .gitignore
    echo "*_token.json" >> .gitignore
    echo "*_session.json" >> .gitignore
    echo "WhatsApp/" >> .gitignore
    echo "Banking/" >> .gitignore
    echo "Payments/" >> .gitignore
    touch .gitkeep
    git add .gitkeep .gitignore
    git commit -m "Initial vault commit"
    cd ..
fi

echo "Vault git repository set up with exclusions."

# Function to start cloud executive
start_cloud_executive() {
    echo "Starting Cloud Executive..."
    python3 orchestrator.py --vault-path ./vault --is-cloud --remote-repo "$1" --sync-interval 30
}

# Function to start local executive
start_local_executive() {
    echo "Starting Local Executive..."
    python3 orchestrator.py --vault-path ./vault --remote-repo "$1" --sync-interval 30
}

# Check arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 [cloud|local] [remote_repo_url]"
    echo "  cloud: Start as Cloud Executive"
    echo "  local: Start as Local Executive"
    echo "  remote_repo_url: Git repository URL for vault sync (optional)"
    echo ""
    echo "Examples:"
    echo "  $0 local                    # Start as Local Executive (local-only)"
    echo "  $0 cloud git@repo:url       # Start as Cloud Executive with sync"
    echo "  $0 local git@repo:url       # Start as Local Executive with sync"
    exit 1
fi

EXECUTIVE_TYPE=$1
REMOTE_REPO=${2:-""}

if [ "$EXECUTIVE_TYPE" = "cloud" ]; then
    echo "Running as Cloud Executive with remote repo: $REMOTE_REPO"
    start_cloud_executive "$REMOTE_REPO"
elif [ "$EXECUTIVE_TYPE" = "local" ]; then
    echo "Running as Local Executive with remote repo: $REMOTE_REPO"
    start_local_executive "$REMOTE_REPO"
else
    echo "Error: Invalid executive type. Use 'cloud' or 'local'."
    exit 1
fi