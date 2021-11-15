import pymongo, json, pytz
from munch import Munch
from datetime import datetime
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from app.constants import DAY_OF_WEEK, REMINDER_ONCE, REMINDER_DAILY, REMINDER_WEEKLY, REMINDER_MONTHLY
from app import database, utils
from app.scheduler import scheduler
from app.constants import Bot
from typing import List, Tuple


class ReminderBuilder:
    '''
    Instantiate a class to handle all messages/callbacks that involves the creation of reminders 
    '''
    def __init__(self, db: pymongo.database.Database):
        self.db = db

    def process_callback(self, callback_query: Munch):
        reminder_in_construction = database.get_reminder_in_construction(
            callback_query.message.chat.id, callback_query['from'].id, self.db)
        timezone = database.query_for_timezone(callback_query.message.chat.id,
                                               self.db)
        current_datetime = pytz.timezone('UTC').localize(
            datetime.now()).astimezone(pytz.timezone(timezone))
        result, key, step = DetailedTelegramCalendar(
            min_date=utils.calculate_date(
                current_datetime, reminder_in_construction['time'])).process(
                    callback_query.data)
        if not result and key:
            Bot.edit_message_text(f"Select {LSTEP[step]}",
                                  callback_query.message.chat.id,
                                  callback_query.message.message_id,
                                  reply_markup=key)
        elif result:
            Bot.edit_message_text(
                f"✅ Reminder set for {result}, {reminder_in_construction['time']}",
                callback_query.message.chat.id,
                callback_query.message.message_id)
            database.update_reminder_in_construction(
                callback_query.message.chat.id,
                callback_query['from'].id,
                self.db,
                frequency=" ".join([REMINDER_ONCE, str(result)]))
            utils.create_reminder(callback_query.message.chat.id,
                                  callback_query['from'].id, self.db)
            database.delete_reminder_in_construction(
                callback_query.message.chat.id, callback_query['from'].id,
                self.db)

    def process_message(self, update: Munch) -> None:
        # reminder text -> reminder time -> reminder frequency -> reminder set.
        if database.is_reminder_time_in_construction(update.message.chat.id,
                                                     update.message['from'].id,
                                                     self.db):
            if utils.is_valid_time(update.message.text):
                # update database
                database.update_reminder_in_construction(
                    update.message.chat.id,
                    update.message['from'].id,
                    self.db,
                    time=update.message.text)
                Bot.send_message(
                    update.message.chat.id,
                    "Once-off reminder or recurring reminder?",
                    reply_to_message_id=update.message.message_id,
                    reply_markup=ReplyKeyboardMarkup(
                        resize_keyboard=True,
                        one_time_keyboard=True,
                        selective=True,
                        keyboard=[[
                            KeyboardButton(REMINDER_ONCE),
                            KeyboardButton(REMINDER_DAILY)
                        ],
                                  [
                                      KeyboardButton(REMINDER_WEEKLY),
                                      KeyboardButton(REMINDER_MONTHLY)
                                  ], [KeyboardButton("🚫 Cancel")]]))
            else:
                # send error message
                Bot.send_message(
                    update.message.chat.id,
                    "Failed to parse time. Please enter time again.",
                    reply_to_message_id=update.message.message_id,
                    reply_markup=ReplyKeyboardMarkup(
                        resize_keyboard=True,
                        one_time_keyboard=True,
                        selective=True,
                        input_field_placeholder=
                        "enter reminder time in <HH>:<MM> format.",
                        keyboard=[[KeyboardButton("🚫 Cancel")]]))
        # enter reminder frequency
        elif database.is_reminder_frequency_in_construction(
                update.message.chat.id, update.message['from'].id, self.db):
            reminder = database.get_reminder_in_construction(
                update.message.chat.id, update.message['from'].id, self.db)

            # create reminder
            if update.message.text == REMINDER_ONCE:
                utils.remove_reply_keyboard_markup(
                    update,
                    self.db,
                    message="once-off reminder selected.",
                    reply_to_message=False)
                database.update_reminder_in_construction(
                    update.message.chat.id,
                    update.message['from'].id,
                    self.db,
                    frequency=REMINDER_ONCE)
                reminder = database.get_reminder_in_construction(
                    update.message.chat.id, update.message['from'].id, self.db)
                timezone = database.query_for_timezone(update.message.chat.id,
                                                       self.db)
                current_datetime = pytz.timezone('UTC').localize(
                    datetime.now()).astimezone(pytz.timezone(timezone))
                utils.show_calendar(update,
                                    min_date=utils.calculate_date(
                                        current_datetime, reminder['time']))
            elif update.message.text == REMINDER_DAILY:
                database.update_reminder_in_construction(
                    update.message.chat.id,
                    update.message['from'].id,
                    self.db,
                    frequency=REMINDER_DAILY)
                reminder = database.get_reminder_in_construction(
                    update.message.chat.id, update.message['from'].id, self.db)
                utils.remove_reply_keyboard_markup(
                    update,
                    self.db,
                    message=
                    f"✅ Reminder set for every day at {reminder['time']}",
                    reply_to_message=False)
                utils.create_reminder(update.message.chat.id,
                                      update.message['from'].id, self.db)
                database.delete_reminder_in_construction(
                    update.message.chat.id, update.message['from'].id, self.db)

            elif update.message.text == REMINDER_WEEKLY:
                database.update_reminder_in_construction(
                    update.message.chat.id,
                    update.message['from'].id,
                    self.db,
                    frequency=REMINDER_WEEKLY)
                Bot.send_message(
                    update.message.chat.id,
                    "Which day of week do you want to set your weekly reminder?",
                    reply_to_message_id=update.message.message_id,
                    reply_markup=ReplyKeyboardMarkup(
                        resize_keyboard=True,
                        one_time_keyboard=True,
                        selective=True,
                        keyboard=[[
                            KeyboardButton("Monday"),
                            KeyboardButton("Tuesday")
                        ],
                                  [
                                      KeyboardButton("Wednesday"),
                                      KeyboardButton("Thursday")
                                  ],
                                  [
                                      KeyboardButton("Friday"),
                                      KeyboardButton("Saturday")
                                  ],
                                  [
                                      KeyboardButton("Sunday"),
                                      KeyboardButton("🚫 Cancel")
                                  ]]))

            elif update.message.text == REMINDER_MONTHLY:
                database.update_reminder_in_construction(
                    update.message.chat.id,
                    update.message['from'].id,
                    self.db,
                    frequency=REMINDER_MONTHLY)
                Bot.send_message(
                    update.message.chat.id,
                    "Which day of the month do you want to set your monthly reminder? (1-31)",
                    reply_to_message_id=update.message.message_id,
                )

            elif reminder['frequency'] == REMINDER_WEEKLY or reminder[
                    'frequency'] == REMINDER_MONTHLY:
                if utils.is_valid_frequency(reminder['frequency'],
                                            update.message.text):
                    day = str(DAY_OF_WEEK[update.message.text]) if reminder[
                        'frequency'] == REMINDER_WEEKLY else update.message.text
                    database.update_reminder_in_construction(
                        update.message.chat.id,
                        update.message['from'].id,
                        self.db,
                        frequency='-'.join([reminder['frequency'], day]))
                    reminder = database.get_reminder_in_construction(
                        update.message.chat.id, update.message['from'].id,
                        self.db)
                    frequency = f"every {update.message.text}" if REMINDER_WEEKLY in reminder[
                        'frequency'] else f"{utils.parse_day_of_month(update.message.text)} of every month"
                    utils.remove_reply_keyboard_markup(
                        update,
                        self.db,
                        message=
                        f"✅ Reminder set for {frequency} at {reminder['time']}",
                        reply_to_message=False)
                    utils.create_reminder(update.message.chat.id,
                                          update.message['from'].id, self.db)
                    database.delete_reminder_in_construction(
                        update.message.chat.id, update.message['from'].id,
                        self.db)
                else:
                    # send error message
                    error_message = "Invalid day of week [1-7]" if reminder[
                        'frequency'] == REMINDER_WEEKLY else "Invalid day of month [1-31]"
                    Bot.send_message(update.message.chat.id, error_message)
        # any text received by bot with no entry in self.db is treated as reminder text
        else:
            database.add_reminder_to_construction(update.message.chat.id,
                                                  update.message['from'].id,
                                                  self.db)
            database.update_reminder_in_construction(
                update.message.chat.id,
                update.message['from'].id,
                self.db,
                reminder_text=update.message.text)
            Bot.send_message(update.message.chat.id,
                             "enter reminder time in <HH>:<MM> format.",
                             reply_to_message_id=update.message.message_id,
                             reply_markup=ReplyKeyboardMarkup(
                                 resize_keyboard=True,
                                 one_time_keyboard=True,
                                 selective=True,
                                 input_field_placeholder=
                                 "enter reminder time in <HH>:<MM> format.",
                                 keyboard=[[KeyboardButton("🚫 Cancel")]]))


class ListReminderMenu:
    '''
    Instantiate a class to handle all the menu buttons for the listing of reminders.
    Should include ability to scroll through pages of reminders in the current chat,
    click into the reminder and be able to delete each reminder through menu button presses.
    '''
    def __init__(self,
                 chat_id: int,
                 db: pymongo.database.Database,
                 max_reminders_per_page: int = 7):
        self.chat_id = chat_id
        self.db = db
        self.max_reminders_per_page = max_reminders_per_page

    def get_reminders(self) -> List[str]:
        reminders = database.query_for_reminders(self.chat_id, self.db)

        reminder_texts = []
        for reminder in reminders:
            if reminder['frequency'].split()[0] == REMINDER_ONCE:
                hour, minute = [int(t) for t in reminder['time'].split(":")]
                time_str = f"{reminder['frequency'].split()[1]}-{hour}-{minute}"
                _frequency = datetime.strptime(
                    time_str, "%Y-%m-%d-%H-%M").strftime("%a, %-d %B %Y")
            elif reminder['frequency'].split('-')[0] == REMINDER_DAILY:
                _frequency = f"everyday"
            elif reminder['frequency'].split('-')[0] == REMINDER_WEEKLY:
                day_of_week = int(reminder['frequency'].split('-')[1])
                for k, v in DAY_OF_WEEK.items():
                    if day_of_week == v:
                        day_of_week = k
                _frequency = f"every {k}"
            elif reminder['frequency'].split('-')[0] == REMINDER_MONTHLY:
                day_of_month = utils.parse_day_of_month(
                    reminder['frequency'].split('-')[1])
                _frequency = f"{day_of_month} of every month"

            reminder['printed_frequency'] = _frequency
            reminder_texts.append(reminder)

        return reminder_texts

    def process(self,
                callback_data: str) -> Tuple[str, InlineKeyboardMarkup, str]:
        _, action, number = callback_data.split("_")
        if action == "page":
            return self.page(int(number))
        elif action == 'reminder':
            return self.get_reminder_menu(int(number))
        elif action == 'delete':
            self.delete_reminder(int(number))
            return self.back_to_list("Reminder has been deleted.")

    def back_to_list(self,
                     message: str) -> Tuple[str, InlineKeyboardMarkup, str]:
        return message, InlineKeyboardMarkup([[
            InlineKeyboardButton(text="Back to list",
                                 callback_data="lr_page_1")
        ]]), None

    def delete_reminder(self, reminder_num: int) -> None:
        try:
            reminder = self.get_reminders()[reminder_num - 1]
        except IndexError:
            return self.back_to_list("😐 Reminder not found found.")
        scheduler.get_job(reminder['job_id']).remove()
        database.delete_reminder(self.chat_id, reminder['reminder_id'],
                                 self.db)

    def get_reminder_menu(
            self, reminder_num: int) -> Tuple[str, InlineKeyboardMarkup, str]:
        '''
        <reminder text>

        Next sending time:
        <date> at <time>

        Frequency:
        <frequency>
        '''
        try:
            reminder = self.get_reminders()[reminder_num - 1]
        except IndexError:
            return self.back_to_list("😐 Reminder not found found.")

        timezone = database.query_for_timezone(self.chat_id, self.db)
        next_trigger_time = scheduler.get_job(
            reminder['job_id']).next_run_time.astimezone(
                pytz.timezone(timezone))
        next_trigger_time = next_trigger_time.strftime(
            "%a, %-d %B %Y at %H:%M")

        message = f"{reminder['reminder_text']}\n\n"
        message += "<b>Next sending time:</b>\n"
        message += f"{next_trigger_time}\n\n"
        message += f"<b>Frequency:</b>\n"
        message += f"{reminder['printed_frequency']} at {reminder['time']}"

        markup = InlineKeyboardMarkup([[
            InlineKeyboardButton(text="Delete",
                                 callback_data=f"lr_delete_{reminder_num}")
        ],
                                       [
                                           InlineKeyboardButton(
                                               text="Back to list",
                                               callback_data="lr_page_1")
                                       ]])
        return message, markup, "html"

    def page(self, page_num: int) -> Tuple[str, InlineKeyboardMarkup, str]:
        '''
        list the reminders in the first page. Max of self.max_reminders_per_page per page
        '''
        try:
            reminder_texts = self.get_reminders()
        except IndexError:
            return "😐 No reminders found.", None, None

        message = ""
        inline_buttons = [[], []]
        reminder_page = reminder_texts[(page_num - 1) *
                                       self.max_reminders_per_page:page_num *
                                       self.max_reminders_per_page]

        if reminder_page == []:
            return 'There are no reminders on current page, try to open another page or request list again.', None, None

        for i, reminder in enumerate(reminder_page):
            number = (page_num - 1) * self.max_reminders_per_page + i + 1
            message += f"{'🖼' if 'file_id' in reminder else '🗓'}{number}){' '*(8 - 2*(len(str(number)) - 1))}{reminder['reminder_text']} ({reminder['printed_frequency']} at {reminder['time']})\n"

            inline_buttons[0].append(
                InlineKeyboardButton(text=f"{number}",
                                     callback_data=f"lr_reminder_{number}"))

        if page_num > 1:
            inline_buttons[1].append(
                InlineKeyboardButton(text=f"<< Page {page_num-1}",
                                     callback_data=f"lr_page_{page_num-1}"))
        if len(reminder_texts) > page_num * self.max_reminders_per_page:
            inline_buttons[1].append(
                InlineKeyboardButton(text=f"Page {page_num+1} >>",
                                     callback_data=f"lr_page_{page_num+1}"))
        markup = InlineKeyboardMarkup(inline_buttons)

        return message, markup, 'html'


class SettingsMenu:
    '''
    Instantiate a class to handle all the keyboard buttons for settings.
    '''
    def __init__(self, chat_id: int, db: pymongo.database.Database):
        self.chat_id = chat_id
        self.db = db

    def process_message(self, text: str) -> None:
        if text == "🕐 Change time zone":
            return self.set_timezone_message()
        else:
            return self.set_timezone(text)

    def list_settings(self) -> None:
        timezone = database.query_for_timezone(self.chat_id, self.db)
        local_current_time = datetime.now(
            pytz.timezone(timezone)).strftime("%H:%M:%S")
        message = "<b>Your current settings:</b>\n\n"
        message += f"- timezone: {timezone}\n"
        message += f"- local time: {local_current_time}"

        markup = ReplyKeyboardMarkup([[
            KeyboardButton(text="🕐 Change time zone"),
            KeyboardButton(text="🚫 Cancel")
        ]],
                                     resize_keyboard=True,
                                     one_time_keyboard=True,
                                     selective=True)

        database.update_chat_settings(self.chat_id,
                                      self.db,
                                      update_settings=True)
        Bot.send_message(self.chat_id,
                         message,
                         reply_markup=markup,
                         parse_mode='html')

    def set_timezone_message(self) -> None:
        message = 'Please type the timezone that you want to change to. For a list of all supported timezones, please click <a href="https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568">here</a>'
        markup = ReplyKeyboardMarkup([[KeyboardButton(text="🚫 Cancel")]],
                                     resize_keyboard=True,
                                     one_time_keyboard=True,
                                     selective=True,
                                     input_field_placeholder="Enter timezone")
        Bot.send_message(self.chat_id,
                         message,
                         reply_markup=markup,
                         parse_mode='html')

    def set_timezone(self, timezone: str) -> None:
        if timezone in pytz.all_timezones:
            message = 'Timezone has been set.'
            database.update_chat_settings(self.chat_id,
                                          self.db,
                                          update_settings=False,
                                          timezone=timezone)
            reminders = database.query_for_reminders(self.chat_id, self.db)
            for reminder in reminders:
                scheduler.get_job(reminder['job_id']).remove()
                hour, minute = [int(t) for t in reminder['time'].split(":")]
                utils.add_scheduler_job(reminder, hour, minute, timezone,
                                        self.chat_id, reminder['reminder_id'],
                                        reminder['job_id'])

            markup = ReplyKeyboardRemove(selective=True)
        else:
            message = 'Timezone not available.\n\n'
            message += 'For a list of all supported timezones, please click <a href="https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568">here</a>'
            markup = ReplyKeyboardMarkup(
                [[KeyboardButton(text="🚫 Cancel")]],
                resize_keyboard=True,
                one_time_keyboard=True,
                selective=True,
                input_field_placeholder="Enter timezone")
        Bot.send_message(self.chat_id,
                         message,
                         reply_markup=markup,
                         parse_mode='html')
