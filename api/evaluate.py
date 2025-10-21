def handler(request):
    if request.method == "POST":
        data = request.json()
        return {
            "statusCode": 200,
            "body": f"Received: {data}"
        }
    return {
        "statusCode": 405,
        "body": "Method Not Allowed"
    }