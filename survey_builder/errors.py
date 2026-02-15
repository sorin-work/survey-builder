from flask import Flask, render_template, request

MESSAGES = {
    400: ("Bad request", "Something about that request did not look right."),
    403: ("Forbidden", "You do not have access to this page."),
    404: ("Page not found", "The page you are looking for does not exist or was removed."),
    405: ("Not allowed", "That action is not available here."),
    500: ("Something went wrong", "An unexpected error happened. Please try again."),
}


def register_error_pages(app: Flask) -> None:
    def handler(error):
        code = getattr(error, "code", 500) or 500
        title, message = MESSAGES.get(code, MESSAGES[500])
        if request.headers.get("HX-Request") == "true":
            return message, code
        return render_template("errors/error.html", title=title, message=message), code

    for code in MESSAGES:
        app.register_error_handler(code, handler)
