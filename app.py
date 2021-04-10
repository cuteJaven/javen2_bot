# chatbot.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackContext, CallbackQueryHandler
# The messageHandler is used for all message updates
import configparser
import logging
import Response as R
import re
import json
import requests


def main():
    # Load your token and create an Updater for your Bot
    config = configparser.ConfigParser()
    config.read('config.ini')
    updater = Updater(token=(config['TELEGRAM']['ACCESS_TOKEN']), use_context=True)  # 1
    dispatcher = updater.dispatcher  # 2
    # You can set this logging module, so you will know when and why things do not work as expected
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    # register a dispatcher to handle message: here we register an echo dispatcher
    dispatcher.add_handler(CommandHandler("start", personal))  # 3
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("calculate", cal_bmr))
    dispatcher.add_handler(CallbackQueryHandler(button))

    dispatcher.add_handler(MessageHandler(Filters.regex(INFO_REGEX), receive_info))
    dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), handle_message))

    # To start the bot:
    updater.start_polling()
    updater.idle()


def help_command(update, context):
    update.message.reply_text("send /start to get started!")


def handle_message(update, context):
    text = str(update.message.text).lower()
    logging.info("Update: " + str(update))
    logging.info("context: " + str(context))
    response = R.sample_responses(text)
    update.message.reply_text(response)


def button(update: Update, context: CallbackContext) -> None:
    # Must call answer!
    update.callback_query.answer()
    # Remove buttons
    update.callback_query.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup([])
    )
    context.user_data[update.effective_chat.id][0] = update.callback_query.data
    update.callback_query.message.reply_text(f'So your gender is {update.callback_query.data}, got it!')
    upload_data(context)


def personal(update: Update, context: CallbackContext) -> None:
    reply_list = [f'Hello {update.effective_user.first_name}']
    chat_id = str(update.effective_chat.id)
    info_dic = download_data(chat_id)
    if info_dic != {}:
        context.user_data[chat_id] = info_dic[chat_id]

    if context.user_data:
        person_info = context.user_data[chat_id]
        reply_list.append('I know these things about you')
        reply_list.extend(
            [f'Your gender is {person_info[0]}',
             f'Your age is {person_info[1]}',
             f'Your height is {person_info[2]}',
             f'Your weight is {person_info[3]}'
             ]
        )
    else:
        reply_list.append('I don\'t know anything about you.')

    # Ask the user to continue entering information
    reply_list.extend([
        'Please tell me about yourself.',
        'Use the format: my gender|age|height|weight is X',
        'For example:',
        'my weight is 50.00kg',
        'my height is 175cm'
    ])
    update.message.reply_text('\n'.join(reply_list))
    if chat_id not in context.user_data:
        context.user_data[chat_id] = ["unknown", "unknown", "unknown", "unknown"]
        reply_buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Male", callback_data='male'),
                InlineKeyboardButton("Female", callback_data='female'),
            ]
        ])
        update.message.reply_text(
            'Firstly, please choose your gender:',
            reply_markup=reply_buttons
        )


INFO_REGEX_GENDER = r'^my gender is (male|female)$'
INFO_REGEX_AGE = r'^my age is ([0-9]*)$'
INFO_REGEX_HEIGHT = r'^my height is ([0-9]+(.[0-9]{1,3})?)cm$'
INFO_REGEX_WEIGHT = r'^my weight is ([0-9]+(.[0-9]{1,3})?)kg$'
INFO_REGEX = r'^my (gender|age|height|weight) is (.*)$'


def receive_info(update: Update, context: CallbackContext) -> None:
    # Creat the information list
    chat_id = str(update.effective_chat.id)
    input_text = update.message.text.lower()
    if chat_id not in context.user_data:
        context.user_data[chat_id] = ["unknown", "unknown", "unknown", "unknown"]
    # gender|age|height|weight
    attribute_list = ['gender', 'age', 'height', 'weight']
    index = -1
    info = []
    if re.match(INFO_REGEX_GENDER, input_text) is not None:
        index = 0
        info = list(re.match(INFO_REGEX_GENDER, input_text).groups())
        context.user_data[chat_id][index] = info[0]
    elif re.match(INFO_REGEX_AGE, input_text) is not None:
        index = 1
        info = list(re.match(INFO_REGEX_AGE, input_text).groups())
        context.user_data[chat_id][index] = info[0]
    elif re.match(INFO_REGEX_HEIGHT, input_text) is not None:
        index = 2
        info = list(re.match(INFO_REGEX_HEIGHT, input_text).groups())
        context.user_data[chat_id][index] = info[0]
    elif re.match(INFO_REGEX_WEIGHT, input_text) is not None:
        index = 3
        info = list(re.match(INFO_REGEX_WEIGHT, input_text).groups())
        context.user_data[chat_id][index] = info[0]

    # Quote the information in the reply
    if index != -1:
        update.message.reply_text(
            f'So your {attribute_list[index]} is {info[0]}, got it!'
        )
        # save the data to database
        upload_data(context)
    else:
        update.message.reply_text(
            "Sorry, I can't understand what you said..."
        )


def upload_data(context):
    json_data = json.dumps(context.user_data)
    requests.put("https://project-ac8ca-default-rtdb.firebaseio.com/.json", data=json_data)


def download_data(chat_id) -> dict:
    response = requests.get("https://project-ac8ca-default-rtdb.firebaseio.com/.json").json()
    if response is None:
        return {}
    else:
        info_dic = response
        if chat_id in info_dic:
            return info_dic
        else:
            return {}


def cal_bmr(update, context):
    chat_id = str(update.effective_chat.id)
    user_data = context.user_data
    flag = 0
    if chat_id in user_data:
        user_data_list = user_data[chat_id]
        for i in user_data_list:
            if i is None:
                update.message.reply_text("please fill all your information in /start")
                break
            flag += 1
        if flag == 4:
            if user_data_list[0] == 'male':
                bmr = (13.75 * float(user_data_list[3])) + (5.003 * float(user_data_list[2])) - (
                        6.755 * float(user_data_list[1])) + 66.47
            elif user_data_list[0] == 'female':
                # 女性
                bmr = (9.563 * float(user_data_list[3])) + (1.85 * float(user_data_list[2])) - (
                        4.676 * float(user_data_list[1])) + 655.1
            else:
                bmr = -1

            if bmr != -1:
                update.message.reply_text(f'Basal Metabolic Rate(kcal / 24hrs):{bmr}')
            else:
                update.message.reply_text('something went wrong, please update your information and try again...')

    else:
        update.message.reply_text("please fill all your information in /start")


if __name__ == '__main__':
    main()
