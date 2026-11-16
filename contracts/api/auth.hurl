# base_url includes /api. Registration identities MUST be fresh on every execution.
# Independent unauthenticated check, even if AC-3 browser instrumentation is unavailable.
GET {{base_url}}/user
HTTP 401

POST {{base_url}}/users
Content-Type: application/json
{
  "user": {
    "username": "{{registration_username}}",
    "email": "{{registration_email}}",
    "password": "{{registration_password}}"
  }
}
HTTP 201
[Captures]
registered_token: jsonpath "$.user.token" redact
[Asserts]
jsonpath "$.user.email" == "{{registration_email}}"
jsonpath "$.user.username" == "{{registration_username}}"
jsonpath "$.user.token" isString
jsonpath "$.user.token" != ""
jsonpath "$.user.token" matches "^[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+$"
jsonpath "$.user.bio" == null
jsonpath "$.user.image" == null

GET {{base_url}}/user
Authorization: Token {{registered_token}}
HTTP 200
[Asserts]
jsonpath "$.user.email" == "{{registration_email}}"

POST {{base_url}}/users/login
Content-Type: application/json
{
  "user": {
    "email": "{{baseline_email}}",
    "password": "{{baseline_password}}"
  }
}
HTTP 200
[Captures]
baseline_token: jsonpath "$.user.token" redact
[Asserts]
jsonpath "$.user.email" == "{{baseline_email}}"
jsonpath "$.user.username" == "{{baseline_username}}"
jsonpath "$.user.token" isString
jsonpath "$.user.token" != ""
jsonpath "$.user.token" matches "^[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+$"
jsonpath "$.user.bio" == null
jsonpath "$.user.image" == null

GET {{base_url}}/user
Authorization: Token {{baseline_token}}
HTTP 200
[Asserts]
jsonpath "$.user.email" == "{{baseline_email}}"

POST {{base_url}}/users/login
Content-Type: application/json
{
  "user": {
    "email": "{{baseline_email}}",
    "password": "{{invalid_password}}"
  }
}
HTTP 422
[Asserts]
jsonpath "$['errors']['email or password'][0]" == "is invalid"

# No Authorization header: authentication cannot leak from a previous request.
GET {{base_url}}/user
HTTP 401
