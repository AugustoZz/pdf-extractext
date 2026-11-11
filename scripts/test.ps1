[CmdletBinding()]
param(
    [ValidateSet("all", "unit", "api", "services", "extractor", "integration", "database", "coverage")]
    [string]$Part = "all",
    [switch]$Docker
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONPATH = $root

function Invoke-ProjectTests {
    param(
        [string[]]$Arguments
    )

    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($uv) {
        & $uv.Source run pytest @Arguments
    } else {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if (-not $python) {
            throw "No se encontró uv ni Python en el PATH."
        }
        & $python.Source -m pytest @Arguments
    }

    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

function Invoke-DockerCommand {
    param(
        [string[]]$Arguments
    )

    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Falló el comando Docker: docker $($Arguments -join ' ')"
    }
}

function Wait-ForMongoHealthy {
    param(
        [int]$TimeoutSeconds = 90
    )

    $containerId = (& docker compose ps -q mongodb).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($containerId)) {
        throw "No se pudo obtener el contenedor de MongoDB."
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $health = (& docker inspect --format "{{.State.Health.Status}}" $containerId).Trim()
        if ($LASTEXITCODE -ne 0) {
            throw "No se pudo consultar la salud del contenedor de MongoDB."
        }
        if ($health -eq "healthy") {
            Write-Host "MongoDB está saludable."
            return
        }
        if ($health -eq "unhealthy") {
            throw "MongoDB quedó en estado unhealthy."
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)

    throw "MongoDB no alcanzó el estado healthy en $TimeoutSeconds segundos."
}

if ($Docker) {
    if ($Part -eq "integration" -or $Part -eq "database") {
        $dockerPath = if ($Part -eq "database") {
            "tests/integration/database"
        } else {
            "tests/integration"
        }
        if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
            throw "Docker no está instalado o no está disponible en el PATH."
        }

        try {
            Write-Host "1/4 Construyendo la imagen de la API..."
            Invoke-DockerCommand @("compose", "build", "api")

            Write-Host "2/4 Iniciando MongoDB..."
            Invoke-DockerCommand @("compose", "up", "-d", "mongodb")

            Write-Host "3/4 Esperando a que MongoDB esté saludable..."
            Wait-ForMongoHealthy

            Write-Host "4/4 Ejecutando $Part..."
            Invoke-DockerCommand @(
                "compose", "run", "--rm", "--no-deps",
                "-e", "PYTHONPATH=/app", "api",
                "uv", "run", "--frozen", "pytest", $dockerPath
            )
        } finally {
            Write-Host "Deteniendo MongoDB..."
            & docker compose stop mongodb | Out-Host
        }
        exit 0
    }

    throw "La opción -Docker solo está disponible para las pruebas de integración."
}

switch ($Part) {
    "all" {
        Invoke-ProjectTests @("tests")
    }
    "unit" {
        Invoke-ProjectTests @("tests/unit")
    }
    "api" {
        Invoke-ProjectTests @("tests/unit/api")
    }
    "services" {
        Invoke-ProjectTests @("tests/unit/services")
    }
    "extractor" {
        Invoke-ProjectTests @("tests/unit/extractor")
    }
    "integration" {
        Invoke-ProjectTests @("tests/integration")
    }
    "database" {
        Invoke-ProjectTests @("tests/integration/database")
    }
    "coverage" {
        Invoke-ProjectTests @("tests", "--cov=app", "--cov-report=term-missing", "--cov-report=html")
    }
}
