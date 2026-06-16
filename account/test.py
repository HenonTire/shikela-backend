import requests

url = "http://127.0.0.1:8000/auth/login/"

payload = {

  "email": "sara.shop@gmail.com",

  "password": "TestPass123!"
}




headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzcyNzQ1MzAwLCJpYXQiOjE3NzI3NDE3MDAsImp0aSI6IjJlNDRhNDYzOTY4ODRhODA5YWQ1ODUzYjQ0MGYyZTQzIiwidXNlcl9pZCI6IjNmNWQ5ODI3LTdmMjYtNDBmOC1hOGM3LThiZjZlMWM1NDY0MSJ9.zQY8KLVeJ2jnJsNRcXTzQKiRIDuarjQU0b7cAGt31kU"
}
response = requests.post(url=url, json=payload)

print(response.status_code)
print(response.json())
print(response.text)
print(response.headers)
print(response.cookies)
print(response.status_code)
