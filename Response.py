from datetime import datetime


def sample_responses(input_text):
    user_message = str(input_text).lower()

    if user_message in ("hello", "hi"):
        return "Hey! How's it going?"
    if user_message in ("who are you?", "what's your name?"):
        return "I'm Javen's robot!"
    if user_message in ("time", "time?"):
        now = datetime.now()
        date_time = now.strftime("%d/%m/%y,%H:%M:%S")
        return str(date_time)
    return "Sorry, I can't understand what you said..."
