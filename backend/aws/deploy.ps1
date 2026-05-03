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

# Load env files: repo root first, then backend/ — backend wins on duplicate keys.
# Shell vars already set always win (we never overwrite non-empty process env).
function Read-DotEnvFileIntoMap([string]$path, [hashtable]$into) {
  if (-not (Test-Path $path)) { return }
  $lines = Get-Content $path -Encoding utf8
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
    $into[$k] = $v
  }
}

$repoRoot = Split-Path $Root -Parent
$merged = @{}
Read-DotEnvFileIntoMap (Join-Path $repoRoot ".env") $merged
Read-DotEnvFileIntoMap (Join-Path $Root ".env") $merged

foreach ($k in $merged.Keys) {
  $v = $merged[$k]
  if ($null -eq $v -or $v -eq "") { continue }
  $current = [Environment]::GetEnvironmentVariable($k, "Process")
  if ([string]::IsNullOrWhiteSpace($current)) {
    [Environment]::SetEnvironmentVariable($k, $v, "Process")
  }
}

if ([string]::IsNullOrWhiteSpace($env:SECRET_KEY)) {
  if (-not [string]::IsNullOrWhiteSpace($merged['SECRET_KEY'])) {
    [Environment]::SetEnvironmentVariable("SECRET_KEY", $merged['SECRET_KEY'], "Process")
  } elseif (-not [string]::IsNullOrWhiteSpace($merged['JWT_SECRET_KEY'])) {
    [Environment]::SetEnvironmentVariable("SECRET_KEY", $merged['JWT_SECRET_KEY'], "Process")
  }
}

Write-Host "Env sources: repo=$repoRoot\.env | backend=$Root\.env (backend overrides)" -ForegroundColor DarkGray

if ([string]::IsNullOrWhiteSpace($env:TELEGRAM_BOT_TOKEN)) {
  Write-Host "WARNING: TELEGRAM_BOT_TOKEN missing — Telegram replies will not work until set (repo or backend .env, or shell env)." -ForegroundColor Yellow
}
if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
  Write-Host "WARNING: DATABASE_URL missing — container falls back to ephemeral SQLite." -ForegroundColor Yellow
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
$EcrToken = (aws ecr get-login-password --region $Region).Trim()
if (-not $EcrToken) { throw "ECR get-login-password returned empty" }
# PowerShell native-pipe mangles stdin encoding; route through cmd.exe so --password-stdin gets clean bytes.
$tokenFile = Join-Path $env:TEMP "ecr_token.txt"
[System.IO.File]::WriteAllText($tokenFile, $EcrToken, [System.Text.UTF8Encoding]::new($false))
try {
  cmd /c "type `"$tokenFile`" | docker login --username AWS --password-stdin $RegistryHost 2>&1"
  if ($LASTEXITCODE -ne 0) { throw "ECR login failed" }
} finally {
  Remove-Item $tokenFile -ErrorAction SilentlyContinue
}

Set-Location $Root
docker build -t "${RepoName}:latest" .
if ($LASTEXITCODE -ne 0) { throw "Docker build failed" }

docker tag "${RepoName}:latest" $EcrImageUri
docker push $EcrImageUri
if ($LASTEXITCODE -ne 0) { throw "Docker push failed" }

$Cors = if ($null -ne $env:CORS_ORIGINS) { $env:CORS_ORIGINS } else { "" }
$DbUrl = if ($null -ne $env:DATABASE_URL) { $env:DATABASE_URL } else { "" }
$TgToken = if ($null -ne $env:TELEGRAM_BOT_TOKEN) { $env:TELEGRAM_BOT_TOKEN } else { "" }
$BaseUrl = if ($null -ne $env:BACKEND_BASE_URL) { $env:BACKEND_BASE_URL } else { "" }

$paramList = @(
  @{ ParameterKey = "EcrImageUri"; ParameterValue = $EcrImageUri }
  @{ ParameterKey = "EcsTaskExecutionRoleArn"; ParameterValue = $EcsTaskExecutionRoleArn }
  @{ ParameterKey = "EcsInfrastructureRoleArn"; ParameterValue = $EcsInfrastructureRoleArn }
  @{ ParameterKey = "GeminiApiKey"; ParameterValue = $env:GEMINI_API_KEY }
  @{ ParameterKey = "SecretKey"; ParameterValue = $env:SECRET_KEY }
  @{ ParameterKey = "CorsOrigins"; ParameterValue = $Cors }
  @{ ParameterKey = "DatabaseUrl"; ParameterValue = $DbUrl }
  @{ ParameterKey = "TelegramBotToken"; ParameterValue = $TgToken }
  @{ ParameterKey = "BackendBaseUrl"; ParameterValue = $BaseUrl }
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

# CloudFormation often reports "No changes" when only the :latest image digest changed — tasks keep the old image unless we force a rollout.
Write-Host "Forcing ECS rollout (cluster default, service nila-api)..." -ForegroundColor Cyan
aws ecs update-service --cluster default --service nila-api --region $Region --force-new-deployment --no-cli-pager | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host "WARNING: ECS force-new-deployment failed (rename cluster/service in deploy.ps1 if yours differ)." -ForegroundColor Yellow
}
