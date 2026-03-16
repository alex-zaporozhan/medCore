# Create test database for pytest (PowerShell).
# Run from project root. Requires Docker container dental_booking_postgres.
# Usage: .\scripts\create_test_db.ps1
# If the database already exists, Postgres will report an error; that is safe to ignore.

$container = "dental_booking_postgres"
$db = "dental_booking_test"
docker exec $container psql -U postgres -c "CREATE DATABASE $db;"
if ($LASTEXITCODE -eq 0) { Write-Host "Database $db created." } else { Write-Host "Exit code $LASTEXITCODE (may mean already exists). Check: docker ps | findstr postgres" }
