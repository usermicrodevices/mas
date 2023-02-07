clear

$api_host = "https://127.0.0.1/api"
$api_login = "test-user"
$api_pass = "test-password"

$uuid = sudo cat /sys/class/dmi/id/product_uuid

$computer_info = lshw -json

$response = curl --request POST --url $api_host/login --header 'Content-Type: application/json' --data '{"username":$api_login,"password":$api_pass}'

curl --request POST --url $api_host/data/devices/$uuid --header 'Authorization: Bearer {0}' -f $response.token --header 'Content-Type: application/json' --data '{"status":1, "extinfo":{0}}' -f $computer_info
