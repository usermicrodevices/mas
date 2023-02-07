clear

$api_host = "https://127.0.0.1/api"
$api_login = "test-user"
$api_pass = "test-password"

$uuid = sudo cat /sys/class/dmi/id/product_uuid

$computer_info = lshw -json

$response = Invoke-WebRequest -Method POST -Body (@{"username"=$api_login; "password"=$api_pass}|ConvertTo-Json) -Uri $api_host/login -ContentType application/json | ConvertFrom-Json

Invoke-WebRequest -Headers @{Authorization = ('Bearer {0}' -f $response.token)} -Method PATCH -Body (@{"status"="1"; "extinfo"=$computer_info} | ConvertTo-Json) -Uri $api_host/data/devices/$uuid -ContentType application/json
