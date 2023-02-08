clear

api_host = "https://127.0.0.1/api"
api_login = "test-user"
api_pass = "test-password"

uuid = $(sudo cat /sys/class/dmi/id/product_uuid)

computer_info = $(lshw -json)

token=$(curl -s --request POST --url $api_host/login --header 'Content-Type: application/json' --data '{"username":"'$api_login'","password":"'$api_pass'"}'|jq -r '.token')

response = $(curl -s -o /dev/null -w "%{http_code}" --request PATCH --url $api_host/data/devices/$uuid --header 'Authorization: Bearer $token' --header 'Content-Type: application/json' --data '{"status":1, "extinfo":'$computer_info'}') 

if test $response -ne 200; then
curl --request POST --url $api_host/data/devices/ --header 'Authorization: Bearer '$token --header 'Content-Type: application/json' --data '{"id":"'$uuid'", "status":1, "extinfo":"'$computer_info'"}'
fi