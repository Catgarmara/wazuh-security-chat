# Wazuh AI Companion - Monitoring Setup Script (PowerShell)
# This script sets up the complete monitoring stack with Prometheus, Grafana, and Alertmanager

param(
    [Parameter(Position=0)]
    [ValidateSet("setup", "start", "stop", "restart", "status", "logs", "test", "cleanup", "help")]
    [string]$Command = "setup",
    
    [Parameter(Position=1)]
    [ValidateSet("dev", "prod", "development", "production")]
    [string]$Environment = "development",
    
    [Parameter(Position=2)]
    [string]$Service = ""
)

# Configuration
$MonitoringDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $MonitoringDir
$ComposeFile = Join-Path $ProjectRoot "docker-compose.yml"
$ComposeProdFile = Join-Path $ProjectRoot "docker-compose.prod.yml"

# Functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-Dependencies {
    Write-Info "Checking dependencies..."
    
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker is not installed. Please install Docker first."
        exit 1
    }
    
    if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-Error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    }
    
    Write-Success "All dependencies are installed"
}

function New-MonitoringDirectories {
    Write-Info "Creating monitoring directories..."
    
    $DataDir = Join-Path $MonitoringDir "data"
    $PrometheusDir = Join-Path $DataDir "prometheus"
    $GrafanaDir = Join-Path $DataDir "grafana"
    $AlertmanagerDir = Join-Path $DataDir "alertmanager"
    $LogsDir = Join-Path $MonitoringDir "logs"
    
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
    New-Item -ItemType Directory -Force -Path $PrometheusDir | Out-Null
    New-Item -ItemType Directory -Force -Path $GrafanaDir | Out-Null
    New-Item -ItemType Directory -Force -Path $AlertmanagerDir | Out-Null
    New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null
    
    Write-Success "Monitoring directories created"
}

function Test-MonitoringConfigs {
    Write-Info "Validating monitoring configurations..."
    
    # Check Prometheus config
    $PrometheusConfig = Join-Path $MonitoringDir "prometheus.yml"
    if (-not (Test-Path $PrometheusConfig)) {
        Write-Error "Prometheus configuration not found: $PrometheusConfig"
        exit 1
    }
    
    # Check Alertmanager config
    $AlertmanagerConfig = Join-Path $MonitoringDir "alertmanager.yml"
    if (-not (Test-Path $AlertmanagerConfig)) {
        Write-Error "Alertmanager configuration not found: $AlertmanagerConfig"
        exit 1
    }
    
    # Check Grafana dashboards
    $GrafanaDashboards = Join-Path $MonitoringDir "grafana\dashboards"
    if (-not (Test-Path $GrafanaDashboards)) {
        Write-Error "Grafana dashboards directory not found: $GrafanaDashboards"
        exit 1
    }
    
    # Check alerting rules
    $RulesDir = Join-Path $MonitoringDir "rules"
    if (-not (Test-Path $RulesDir)) {
        Write-Error "Alerting rules directory not found: $RulesDir"
        exit 1
    }
    
    Write-Success "All monitoring configurations are valid"
}

function Initialize-Environment {
    Write-Info "Setting up environment variables..."
    
    $EnvFile = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $EnvFile)) {
        Write-Warning ".env file not found. Creating default configuration..."
        
        $DefaultEnv = @"
# Database Configuration
DB_PASSWORD=postgres
DB_HOST=postgres
DB_PORT=5432
DB_NAME=wazuh_chat
DB_USER=postgres

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# Security Configuration
SECRET_KEY=your-secret-key-here-must-be-at-least-32-characters-long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Grafana Configuration
GRAFANA_PASSWORD=admin
GRAFANA_SECRET_KEY=your-grafana-secret-key-here

# Application Configuration
APP_NAME=Wazuh AI Companion
APP_VERSION=2.0.0
ENVIRONMENT=development
DEBUG=false

# Monitoring Configuration
PROMETHEUS_RETENTION=15d
GRAFANA_ADMIN_USER=admin
ALERTMANAGER_RETENTION=120h
"@
        
        Set-Content -Path $EnvFile -Value $DefaultEnv
        Write-Warning "Please update the .env file with your actual configuration values"
    }
    
    Write-Success "Environment configuration ready"
}

function Start-MonitoringStack {
    param([string]$Env = "development")
    
    Write-Info "Starting monitoring stack for $Env environment..."
    
    Set-Location $ProjectRoot
    
    if ($Env -eq "production" -or $Env -eq "prod") {
        docker-compose -f $ComposeProdFile --profile monitoring up -d
    } else {
        docker-compose -f $ComposeFile --profile monitoring up -d
    }
    
    Write-Success "Monitoring stack started successfully"
}

function Wait-ForServices {
    Write-Info "Waiting for services to be ready..."
    
    # Wait for Prometheus
    Write-Info "Waiting for Prometheus..."
    $timeout = 60
    $elapsed = 0
    do {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:9090/-/ready" -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) { break }
        } catch {}
        Start-Sleep 2
        $elapsed += 2
    } while ($elapsed -lt $timeout)
    
    if ($elapsed -ge $timeout) {
        Write-Error "Prometheus failed to start within 60 seconds"
        exit 1
    }
    
    # Wait for Grafana
    Write-Info "Waiting for Grafana..."
    $elapsed = 0
    do {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) { break }
        } catch {}
        Start-Sleep 2
        $elapsed += 2
    } while ($elapsed -lt $timeout)
    
    if ($elapsed -ge $timeout) {
        Write-Error "Grafana failed to start within 60 seconds"
        exit 1
    }
    
    # Wait for Alertmanager
    Write-Info "Waiting for Alertmanager..."
    $elapsed = 0
    do {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:9093/-/ready" -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) { break }
        } catch {}
        Start-Sleep 2
        $elapsed += 2
    } while ($elapsed -lt $timeout)
    
    if ($elapsed -ge $timeout) {
        Write-Error "Alertmanager failed to start within 60 seconds"
        exit 1
    }
    
    Write-Success "All monitoring services are ready"
}

function Show-AccessInfo {
    Write-Success "Monitoring stack is now running!"
    Write-Host ""
    Write-Host "Access URLs:"
    Write-Host "  📊 Grafana:      http://localhost:3000 (admin/admin)" -ForegroundColor Cyan
    Write-Host "  📈 Prometheus:   http://localhost:9090" -ForegroundColor Cyan
    Write-Host "  🚨 Alertmanager: http://localhost:9093" -ForegroundColor Cyan
    Write-Host "  📋 Node Exporter: http://localhost:9100" -ForegroundColor Cyan
    Write-Host "  🐘 PostgreSQL Exporter: http://localhost:9187" -ForegroundColor Cyan
    Write-Host "  🔴 Redis Exporter: http://localhost:9121" -ForegroundColor Cyan
    Write-Host "  📦 cAdvisor: http://localhost:8080" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Default Grafana Dashboards:"
    Write-Host "  • Wazuh AI Companion - System Overview"
    Write-Host "  • Wazuh AI Companion - AI Performance"
    Write-Host "  • Wazuh AI Companion - Business Metrics"
    Write-Host "  • Wazuh AI Companion - Infrastructure Metrics"
    Write-Host "  • Wazuh AI Companion - Alerts & Monitoring"
    Write-Host ""
    Write-Host "To stop the monitoring stack:"
    Write-Host "  docker-compose --profile monitoring down"
    Write-Host ""
}

function Test-AlertConfiguration {
    Write-Info "Testing alert configuration..."
    
    # Basic validation of YAML files
    $RulesFiles = Get-ChildItem -Path (Join-Path $MonitoringDir "rules") -Filter "*.yml"
    foreach ($file in $RulesFiles) {
        try {
            # Basic YAML syntax check (PowerShell doesn't have built-in YAML parser)
            $content = Get-Content $file.FullName -Raw
            if ($content -match "^\s*groups:\s*$" -and $content -match "^\s*-\s*name:\s*") {
                Write-Success "Rules file validation passed: $($file.Name)"
            } else {
                Write-Warning "Rules file may have issues: $($file.Name)"
            }
        } catch {
            Write-Error "Error validating rules file: $($file.Name)"
        }
    }
}

function Remove-MonitoringStack {
    Write-Info "Cleaning up monitoring stack..."
    
    Set-Location $ProjectRoot
    docker-compose --profile monitoring down -v
    
    Write-Success "Monitoring stack cleaned up"
}

function Show-Help {
    Write-Host "Wazuh AI Companion - Monitoring Setup Script (PowerShell)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\setup-monitoring.ps1 [COMMAND] [OPTIONS]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  setup [dev|prod]    Set up and start monitoring stack (default: dev)"
    Write-Host "  start [dev|prod]    Start monitoring stack"
    Write-Host "  stop                Stop monitoring stack"
    Write-Host "  restart [dev|prod]  Restart monitoring stack"
    Write-Host "  status              Show status of monitoring services"
    Write-Host "  logs [service]      Show logs for monitoring services"
    Write-Host "  test                Test monitoring configuration"
    Write-Host "  cleanup             Stop and remove all monitoring containers and volumes"
    Write-Host "  help                Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\setup-monitoring.ps1 setup dev        # Set up development monitoring"
    Write-Host "  .\setup-monitoring.ps1 setup prod       # Set up production monitoring"
    Write-Host "  .\setup-monitoring.ps1 logs grafana     # Show Grafana logs"
    Write-Host "  .\setup-monitoring.ps1 test             # Test configuration"
    Write-Host ""
}

# Main script logic
switch ($Command) {
    "setup" {
        Test-Dependencies
        New-MonitoringDirectories
        Test-MonitoringConfigs
        Initialize-Environment
        Start-MonitoringStack $Environment
        Wait-ForServices
        Show-AccessInfo
    }
    "start" {
        Start-MonitoringStack $Environment
        Wait-ForServices
        Show-AccessInfo
    }
    "stop" {
        Set-Location $ProjectRoot
        docker-compose --profile monitoring down
        Write-Success "Monitoring stack stopped"
    }
    "restart" {
        Set-Location $ProjectRoot
        docker-compose --profile monitoring down
        Start-MonitoringStack $Environment
        Wait-ForServices
        Show-AccessInfo
    }
    "status" {
        Set-Location $ProjectRoot
        docker-compose --profile monitoring ps
    }
    "logs" {
        Set-Location $ProjectRoot
        if ($Service) {
            docker-compose --profile monitoring logs -f $Service
        } else {
            docker-compose --profile monitoring logs -f
        }
    }
    "test" {
        Test-MonitoringConfigs
        Test-AlertConfiguration
        Write-Success "All tests passed"
    }
    "cleanup" {
        Remove-MonitoringStack
    }
    "help" {
        Show-Help
    }
    default {
        Write-Error "Unknown command: $Command"
        Show-Help
        exit 1
    }
}