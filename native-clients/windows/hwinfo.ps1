clear

$api_host = "https://127.0.0.1/api"
$api_login = "test-user"
$api_pass = "test-password"

$uuid = Get-WmiObject Win32_ComputerSystemProduct  | Select-Object -ExpandProperty UUID

$computer_info = Get-ComputerInfo | ConvertTo-Json

$response = Invoke-WebRequest -Method POST -Body (@{"username"=$api_login; "password"=$api_pass}|ConvertTo-Json) -Uri $api_host/login -ContentType application/json | ConvertFrom-Json

try
{
$response = Invoke-WebRequest -Headers @{Authorization = ('Bearer {0}' -f $response.token)} -Method PATCH -Body (@{"status"="1"; "extinfo"=$computer_info} | ConvertTo-Json) -Uri $api_host/data/devices/$uuid -ContentType application/json
$StatusCode = $response.StatusCode
} catch {
$StatusCode = $_.Exception.Response.StatusCode.value__
}
if ($StatusCode -ne 200){
Invoke-WebRequest -Headers @{Authorization = ('Bearer {0}' -f $response.token)} -Method POST -Body (@{"id"=$uuid, "status"="1"; "extinfo"=$computer_info} | ConvertTo-Json) -Uri $api_host/data/devices/ -ContentType application/json
}