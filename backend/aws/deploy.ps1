# Deploy Nila FastAPI backend to Amazon ECS Express Mode + ECR (recommended App Runner successor).
# Prerequisites: AWS CLI v2, Docker, and credentials (aws configure or env vars).
#
#   $env:GEMINI_API_KEY = "..."
#   $env:SECRET_KEY = "..."   # long random string for JWT
# Optional:
#   $env:AWS_REGION = "us-east-1"
#   $env:CORS_ORIGINS = "https://your-frontend.vercel.app,http://localhost:5173"
#   $env:DATABASE_URL = "postgresql://...?sslmode=require"
#
# Then:  cd D:\nila\backend\aws
#         .\deploy.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Cfn = Join-Path $PSScriptRoot "cloudformation"
$BaseTemplate = Join-Path $Cfn "01-base.yaml"
$AppTemplate = Join-Path $Cfn "02-ecs-express.yaml"

$Region = if ($env:AWS_REGION) { $env:AWS_REGION } else { "us-east-1" }
$BaseStack = "nila-aws-base"
$AppStack = "nila-aws-app"
$RepoName = "nila-backend"

function Require-Tool($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Required command not found: $name"
  }
}
Require-Tool aws
Require-Tool docker

Write-Host "Checking AWS credentials..." -ForegroundColor Cyan
$null = aws sts get-caller-identity 2>&1
if ($LASTEXITCODE -ne 0) { throw "AWS CLI is not configured. Run: aws configure" }
$AccountId = (aws sts get-caller-identity --query Account --output text).Trim()
Write-Host "Account: $AccountId  Region: $Region" -ForegroundColor Green

# Optional: load $Root/.env (backend) — env vars already set in the shell take precedence
$dotenv = Join-Path $Root ".env"
if (Test-Path $dotenv) {
  $lines = Get-Content $dotenv -Encoding utf8
  $map = @{}
  foreach ($line in $lines) {
    $t = $line.Trim()
    if (-not $t -or $t.StartsWith("#")) { continue }
    $eq = $t.IndexOf("=")
    if ($eq -lt 1) { continue }
    $k = $t.Substring(0, $eq).Trim()
    $v = $t.Substring($eq + 1).Trim()
    if ($v.Length -ge 2 -and (($v.StartsWith([char]34) -and $v.EndsWith([char]34)) -or ($v.StartsWith([char]39) -and $v.EndsWith([char]39)))) {
      $v = $v.Substring(1, $v.Length - 2)
    }
    $map[$k] = $v
  }
  if (-not $env:GEMINI_API_KEY -and $map['GEMINI_API_KEY']) { $env:GEMINI_API_KEY = $map['GEMINI_API_KEY'] }
  if (-not $env:SECRET_KEY) {
    if ($map['SECRET_KEY']) { $env:SECRET_KEY = $map['SECRET_KEY'] }
    elseif ($map['JWT_SECRET_KEY']) { $env:SECRET_KEY = $map['JWT_SECRET_KEY'] }
  }
  if (-not $env:CORS_ORIGINS -and $map['CORS_ORIGINS']) { $env:CORS_ORIGINS = $map['CORS_ORIGINS'] }
  if (-not $env:DATABASE_URL -and $map['DATABASE_URL']) { $env:DATABASE_URL = $map['DATABASE_URL'] }
}

if (-not $env:GEMINI_API_KEY -or -not $env:SECRET_KEY) {
  throw "Set GEMINI_API_KEY and SECRET_KEY before running (JWT signing needs SECRET_KEY)."
}

Write-Host "Deploying stack $BaseStack (ECR + IAM)..." -ForegroundColor Cyan
aws cloudformation deploy `
  --template-file $BaseTemplate `
  --stack-name $BaseStack `
  --parameter-overrides "RepositoryName=$RepoName" `
  --capabilities CAPABILITY_NAMED_IAM `
  --region $Region
if ($LASTEXITCODE -ne 0) { throw "Base stack deploy failed" }

$EcrImageUri = (aws cloudformation describe-stacks --stack-name $BaseStack --region $Region --query "Stacks[0].Outputs[?OutputKey=='EcrImageUri'].OutputValue" --output text).Trim()
$EcsTaskExecutionRoleArn = (aws cloudformation describe-stacks --stack-name $BaseStack --region $Region --query "Stacks[0].Outputs[?OutputKey=='EcsTaskExecutionRoleArn'].OutputValue" --output text).Trim()
$EcsInfrastructureRoleArn = (aws cloudformation describe-stacks --stack-name $BaseStack --region $Region --query "Stacks[0].Outputs[?OutputKey=='EcsExpressInfrastructureRoleArn'].OutputValue" --output text).Trim()
$RegistryHost = "${AccountId}.dkr.ecr.${Region}.amazonaws.com"

if (-not $EcrImageUri) { throw "Could not read EcrImageUri from stack outputs" }
if (-not $EcsTaskExecutionRoleArn -or -not $EcsInfrastructureRoleArn) {
  throw "Could not read ECS role ARNs from base stack. Re-deploy $BaseStack or migrate from an older template (App Runner roles removed)."
}

Write-Host "Building and pushing image..." -ForegroundColor Cyan
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $RegistryHost
if ($LASTEXITCODE -ne 0) { throw "ECR login failed" }

Set-Location $Root
docker build -t "${RepoName}:latest" .
if ($LASTEXITCODE -ne 0) { throw "Docker build failed" }

docker tag "${RepoName}:latest" $EcrImageUri
docker push $EcrImageUri
if ($LASTEXITCODE -ne 0) { throw "Docker push failed" }

$Cors = if ($null -ne $env:CORS_ORIGINS) { $env:CORS_ORIGINS } else { "" }
$DbUrl = if ($null -ne $env:DATABASE_URL) { $env:DATABASE_URL } else { "" }

$paramList = @(
  @{ ParameterKey = "EcrImageUri"; ParameterValue = $EcrImageUri }
  @{ ParameterKey = "EcsTaskExecutionRoleArn"; ParameterValue = $EcsTaskExecutionRoleArn }
  @{ ParameterKey = "EcsInfrastructureRoleArn"; ParameterValue = $EcsInfrastructureRoleArn }
  @{ ParameterKey = "GeminiApiKey"; ParameterValue = $env:GEMINI_API_KEY }
  @{ ParameterKey = "SecretKey"; ParameterValue = $env:SECRET_KEY }
  @{ ParameterKey = "CorsOrigins"; ParameterValue = $Cors }
  @{ ParameterKey = "DatabaseUrl"; ParameterValue = $DbUrl }
)
# AWS CLI on Windows: file:// + absolute path with backslashes (not /C:/... URI) loads reliably
$paramPath = Join-Path $PSScriptRoot "._cfn_param_overrides.json"
$paramJson = $paramList | ConvertTo-Json -Depth 5
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($paramPath, $paramJson, $utf8NoBom)
$paramFileArg = "file://$((Resolve-Path $paramPath).Path)"

Write-Host "Deploying stack $AppStack (ECS Express Mode)..." -ForegroundColor Cyan
aws cloudformation deploy `
  --template-file $AppTemplate `
  --stack-name $AppStack `
  --parameter-overrides $paramFileArg `
  --region $Region
if ($LASTEXITCODE -ne 0) { throw "App stack deploy failed" }

Remove-Item $paramPath -ErrorAction SilentlyContinue

$Url = (aws cloudformation describe-stacks --stack-name $AppStack --region $Region --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text).Trim()
$displayUrl = if ($Url -match "^\s*https?://") { $Url.Trim() } else { "https://$($Url.Trim())" }
Write-Host ""
Write-Host "API base: $displayUrl" -ForegroundColor Green
Write-Host "Point the frontend (e.g. config.ts API_URL) at this origin. Re-run CORS: set CORS_ORIGINS to include your Vercel URL and update the app stack (or re-run this script)." -ForegroundColor Yellow
