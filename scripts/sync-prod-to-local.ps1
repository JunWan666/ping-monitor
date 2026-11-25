param(
    [Parameter(Mandatory = $true)]
    [string]$Remote,   # 例：root@你的服务器IP
    [string]$RemoteProjectDir = "/opt/ping-monitor",
    [string]$RemoteMysqlContainer = "ping-monitor-mysql",
    [string]$RemoteDatabase = "ping_monitor",
    [string]$LocalMysqlContainer = "ping-monitor-mysql",
    [string]$LocalRedisContainer = "ping-monitor-redis",
    [string]$LocalDatabase = "ping_monitor",
    [string]$LocalMysqlRootPassword = "change-me",
    [switch]$SkipRemoteDump,
    [switch]$SkipAppStart
)

$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Set-DotEnvValue {
    param(
        [string]$Path,
        [string]$Name,
        [string]$Value
    )

    $line = "$Name=$Value"
    if (-not (Test-Path -LiteralPath $Path)) {
        Set-Content -LiteralPath $Path -Value $line -Encoding UTF8
        return
    }

    $lines = Get-Content -LiteralPath $Path
    $updated = $false
    $newLines = @(
        foreach ($item in $lines) {
        if ($item -match "^\s*#?\s*$([regex]::Escape($Name))=") {
            $updated = $true
            $line
        }
        else {
            $item
        }
    }
    )

    if (-not $updated) {
        $newLines += $line
    }
    Set-Content -LiteralPath $Path -Value $newLines -Encoding UTF8
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList
    )

    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($ArgumentList -join ' ')"
    }
}

function Invoke-LocalMysqlQuery {
    param([string]$Sql)

    $output = & docker exec -e "MYSQL_PWD=$LocalMysqlRootPassword" $LocalMysqlContainer mysql -uroot -N -B $LocalDatabase -e $Sql
    if ($LASTEXITCODE -ne 0) {
        throw "Local MySQL query failed: $Sql"
    }
    return @($output | ForEach-Object { "$_".Trim() } | Where-Object { $_ })
}

Require-Command ssh
Require-Command scp
Require-Command docker

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backupDir = Join-Path $repoRoot "data\prod-backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$dumpName = "${LocalDatabase}_${timestamp}.sql.gz"
$remoteDump = "$RemoteProjectDir/data/backups/$dumpName"
$localDump = Join-Path $backupDir $dumpName
$sshOptions = @("-o", "StrictHostKeyChecking=accept-new")

if (-not $SkipRemoteDump) {
    Write-Host "Creating remote MySQL dump on $Remote ..."
    $remoteCommand = @"
set -e
mkdir -p '$RemoteProjectDir/data/backups'
docker exec $RemoteMysqlContainer sh -lc 'mysqldump -uroot -p"`$MYSQL_ROOT_PASSWORD" --single-transaction --quick --routines --triggers --events --default-character-set=utf8mb4 $RemoteDatabase' | gzip -c > '$remoteDump'
ls -lh '$remoteDump'
"@
    Invoke-Checked -FilePath "ssh" -ArgumentList ($sshOptions + @($Remote, $remoteCommand))

    Write-Host "Downloading dump to $localDump ..."
    Invoke-Checked -FilePath "scp" -ArgumentList ($sshOptions + @("${Remote}:$remoteDump", $localDump))
}
elseif (-not (Test-Path -LiteralPath $localDump)) {
    $latest = Get-ChildItem -LiteralPath $backupDir -Filter "*.sql.gz" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) {
        throw "No local dump found in $backupDir"
    }
    $localDump = $latest.FullName
    $dumpName = $latest.Name
    Write-Host "Using latest local dump: $localDump"
}

$envPath = Join-Path $repoRoot ".env"
Set-DotEnvValue -Path $envPath -Name "DISABLE_NOTIFICATIONS" -Value "true"
Set-DotEnvValue -Path $envPath -Name "DISABLE_SCHEDULER" -Value "true"
Write-Host "Local .env safety switches set: DISABLE_NOTIFICATIONS=true, DISABLE_SCHEDULER=true"

Push-Location $repoRoot
try {
    Write-Host "Starting local MySQL and Redis ..."
    Invoke-Checked -FilePath "docker" -ArgumentList @("compose", "--env-file", ".env", "-f", "docker/docker-compose.yml", "up", "-d", "mysql", "redis")

    Write-Host "Waiting for local MySQL ..."
    $mysqlReady = $false
    for ($i = 1; $i -le 60; $i++) {
        & docker exec -e "MYSQL_PWD=$LocalMysqlRootPassword" $LocalMysqlContainer mysqladmin ping -uroot --silent *> $null
        if ($LASTEXITCODE -eq 0) {
            $mysqlReady = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $mysqlReady) {
        throw "Local MySQL did not become ready"
    }

    Write-Host "Resetting local database $LocalDatabase ..."
    Invoke-Checked -FilePath "docker" -ArgumentList @(
        "exec",
        "-e", "MYSQL_PWD=$LocalMysqlRootPassword",
        $LocalMysqlContainer,
        "mysql",
        "-uroot",
        "-e",
        "DROP DATABASE IF EXISTS $LocalDatabase; CREATE DATABASE $LocalDatabase CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    )

    Write-Host "Copying dump into local MySQL container ..."
    Invoke-Checked -FilePath "docker" -ArgumentList @("cp", $localDump, "${LocalMysqlContainer}:/tmp/$dumpName")

    Write-Host "Importing production data locally ..."
    Invoke-Checked -FilePath "docker" -ArgumentList @(
        "exec",
        "-e", "MYSQL_PWD=$LocalMysqlRootPassword",
        $LocalMysqlContainer,
        "sh",
        "-lc",
        "gunzip -c /tmp/$dumpName | mysql -uroot $LocalDatabase"
    )

    Write-Host "Clearing notification targets and credentials inside local database ..."
    # Every system_config column that lets the app push outside this machine.
    $secretColumns = @(
        "serverchan_key",
        "webhook_url", "webhook_secret",                      # host alerts (DingTalk)
        "domain_webhook_url", "domain_webhook_secret",        # domain alerts (DingTalk)
        "report_webhook_url", "report_webhook_secret",        # reports (DingTalk)
        "sms_access_key_id", "sms_access_key_secret",         # domain alerts (Aliyun SMS)
        "sms_sign_name", "sms_template_code", "sms_phone_numbers"
    )
    $reportSwitches = @("daily_report_enabled", "weekly_report_enabled", "monthly_report_enabled")

    # An older production schema may not have the domain/SMS columns yet; only touch the ones that exist.
    # Columns the app adds later on startup are created empty.
    $wanted = ($secretColumns + $reportSwitches + @("notification_mode") | ForEach-Object { "'$_'" }) -join ", "
    $existing = Invoke-LocalMysqlQuery "SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'system_config' AND COLUMN_NAME IN ($wanted);"
    $presentSecrets = @($secretColumns | Where-Object { $existing -contains $_ })
    if ($presentSecrets.Count -eq 0) {
        throw "system_config has none of the expected notification columns; local app was not started"
    }

    $assignments = @($presentSecrets | ForEach-Object { "$_ = NULL" })
    $assignments += @($reportSwitches | Where-Object { $existing -contains $_ } | ForEach-Object { "$_ = 0" })
    if ($existing -contains "notification_mode") {
        $assignments += "notification_mode = 'status_change'"
    }
    Invoke-LocalMysqlQuery "UPDATE system_config SET $($assignments -join ', ');" | Out-Null

    $leftCheck = ($presentSecrets | ForEach-Object { "COALESCE($_, '') <> ''" }) -join " OR "
    $left = Invoke-LocalMysqlQuery "SELECT COUNT(*) FROM system_config WHERE $leftCheck;"
    if ($left.Count -ne 1 -or $left[0] -ne "0") {
        throw "Notification credentials are still present in local system_config; local app was not started"
    }
    Write-Host "Cleared: $($presentSecrets -join ', ')"

    Write-Host "Flushing local Redis cache if available ..."
    & docker exec $LocalRedisContainer redis-cli FLUSHDB *> $null

    if (-not $SkipAppStart) {
        Write-Host "Starting local app with notification and scheduler disabled ..."
        Invoke-Checked -FilePath "docker" -ArgumentList @("compose", "--env-file", ".env", "-f", "docker/docker-compose.yml", "up", "-d", "--build", "--force-recreate", "ping-monitor")
    }

    Write-Host "Done. Local data is ready. Open http://localhost:8000"
    Write-Host "Dump saved at: $localDump"
}
finally {
    Pop-Location
}
