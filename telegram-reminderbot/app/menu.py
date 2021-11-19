import pytz, uuid
from munch import Munch
from datetime import datetime, timedelta
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from app.constants import DAY_OF_WEEK, REMINDER_ONCE, REMINDER_DAILY, REMINDER_WEEKLY, REMINDER_MONTHLY
from app import utils
from app.scheduler import scheduler
from app.constants import Bot
from app.database import Database
from typing import List, Tuple


class ReminderBuilder:
    '''
    Instantiate a class to handle all messages/callbacks that involves the creation of reminders 
    '''
    def __init__(self, db: Database):
        self.database = db

    def process_callback(self, callback_query: Munch):
        reminder_in_construction = self.database.get_reminder_in_construction(
            callback_query['from'].id)
        timezone = self.database.query_for_timezone()
        reminder_time = utils.convert_time_str(
            reminder_in_construction['time'], timezone)

        current_datetime = pytz.utc.localize(datetime.now())
        result, key, step = DetailedTelegramCalendar(
            min_date=utils.calculate_date(
                current_datetime, reminder_time)).process(callback_query.data)
        if not result and key:
            Bot.edit_message_text(f"Select {LSTEP[step]}",
                                  callback_query.message.chat.id,
                                  callback_query.message.message_id,
                                  reply_markup=key)
        elif result:
            Bot.edit_message_text(
                f"✅ Reminder set for {result}, {reminder_time}",
                callback_query.message.chat.id,
                callback_query.message.message_id)
            _date = pytz.timezone(timezone).localize(
                datetime.strptime(f"{result}, {reminder_time}",
                                  "%Y-%m-%d, %H:%M")).astimezone(
                                      pytz.utc).strftime('%Y-%m-%d')
            self.database.update_reminder_in_construction(
                callback_query['from'].id,
                frequency=" ".join([REMINDER_ONCE, _date]))
            utils.create_reminder(callback_query.message.chat.id,
                                  callback_query['from'].id, self.database)
            self.database.delete_reminder_in_construction(
                callback_query['from'].id)

    def process_message(self, update: Munch) -> None:
        # reminder text -> reminder time -> reminder frequency -> reminder set.
        if self.database.is_reminder_time_in_construction(
                update.message['from'].id):
            if utils.is_valid_time(update.message.text):
                # update database
                timezone = self.database.query_for_timezone()
                hour, minute = [int(t) for t in update.message.text.split(":")]
                _time = pytz.timezone(timezone).localize(
                    datetime.now()).replace(hour=hour,
                                            minute=minute).astimezone(
                                                pytz.utc).strftime("%H:%M")
                self.database.update_reminder_in_construction(
                    update.message['from'].id, time=_time)
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
        elif self.database.is_reminder_frequency_in_construction(
                update.message['from'].id):
            reminder = self.database.get_reminder_in_construction(
                update.message['from'].id)

            # create reminder
            if update.message.text == REMINDER_ONCE:
                utils.remove_reply_keyboard_markup(
                    update,
                    message="once-off reminder selected.",
                    reply_to_message=False)
                self.database.update_reminder_in_construction(
                    update.message['from'].id, frequency=REMINDER_ONCE)
                reminder = self.database.get_reminder_in_construction(
                    update.message['from'].id)
                timezone = self.database.query_for_timezone()
                utils.show_calendar(
                    update,
                    min_date=utils.calculate_date(
                        pytz.utc.localize(datetime.now()),
                        utils.convert_time_str(
                            reminder['time'],
                            self.database.query_for_timezone())))
            elif update.message.text == REMINDER_DAILY:
                self.database.update_reminder_in_construction(
                    update.message['from'].id, frequency=REMINDER_DAILY)
                reminder = self.database.get_reminder_in_construction(
                    update.message['from'].id)
                utils.create_reminder(update.message.chat.id,
                                      update.message['from'].id, self.database)
                utils.remove_reply_keyboard_markup(
                    update,
                    message=
                    f"✅ Reminder set for every day at {utils.convert_time_str(reminder['time'], self.database.query_for_timezone())}",
                    reply_to_message=False)
                self.database.delete_reminder_in_construction(
                    update.message['from'].id)

            elif update.message.text == REMINDER_WEEKLY:
                self.database.update_reminder_in_construction(
                    update.message['from'].id, frequency=REMINDER_WEEKLY)
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
                self.database.update_reminder_in_construction(
                    update.message['from'].id, frequency=REMINDER_MONTHLY)
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
                    self.database.update_reminder_in_construction(
                        update.message['from'].id,
                        frequency='-'.join([reminder['frequency'], day]))
                    reminder = self.database.get_reminder_in_construction(
                        update.message['from'].id)
                    frequency = f"every {update.message.text}" if REMINDER_WEEKLY in reminder[
                        'frequency'] else f"{utils.parse_day_of_month(update.message.text)} of every month"
                    utils.create_reminder(update.message.chat.id,
                                          update.message['from'].id,
                                          self.database)
                    utils.remove_reply_keyboard_markup(
                        update,
                        message=
                        f"✅ Reminder set for {frequency} at {utils.convert_time_str(reminder['time'], self.database.query_for_timezone())}",
                        reply_to_message=False)
                    self.database.delete_reminder_in_construction(
                        update.message['from'].id)
                else:
                    # send error message
                    error_message = "Invalid day of week [1-7]" if reminder[
                        'frequency'] == REMINDER_WEEKLY else "Invalid day of month [1-31]"
                    Bot.send_message(update.message.chat.id, error_message)
        # any text received by bot with no entry in self.database is treated as reminder text
        else:
            self.database.add_reminder_to_construction(
                update.message['from'].id)
            if 'file_id' in update.message:
                self.database.update_reminder_in_construction(
                    update.message['from'].id,
                    reminder_text=update.message.text,
                    file_id=update.message.file_id)
            else:
                self.database.update_reminder_in_construction(
                    update.message['from'].id,
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
                 db: Database,
                 max_reminders_per_page: int = 7):
        self.chat_id = chat_id
        self.database = db
        self.max_reminders_per_page = max_reminders_per_page

    def get_reminders(self) -> List[str]:
        reminders = self.database.query_for_reminders()
        timezone = self.database.query_for_timezone()
        reminder_texts = []
        for reminder in reminders:
            if reminder['frequency'].split()[0] == REMINDER_ONCE:
                hour, minute = [int(t) for t in reminder['time'].split(":")]
                time_str = f"{reminder['frequency'].split()[1]}-{hour}-{minute}"
                _frequency = pytz.utc.localize(
                    datetime.strptime(time_str, "%Y-%m-%d-%H-%M")).astimezone(
                        pytz.timezone(timezone)).strftime("%a, %-d %B %Y")
            elif reminder['frequency'].split('-')[0] == REMINDER_DAILY:
                _frequency = f"everyday"
            elif reminder['frequency'].split('-')[0] == REMINDER_WEEKLY:
                day_of_week = int(reminder['frequency'].split('-')[1])
                for k, v in DAY_OF_WEEK.items():
                    if day_of_week == v:
                        day_of_week = k

                _frequency = f"every {day_of_week}"
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
        self.database.delete_reminder(reminder['reminder_id'])

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

        timezone = self.database.query_for_timezone()
        next_trigger_time = scheduler.get_job(
            reminder['job_id']).next_run_time.astimezone(
                pytz.timezone(timezone))
        next_trigger_time = next_trigger_time.strftime(
            "%a, %-d %B %Y at %H:%M")

        message = f"{reminder['reminder_text']}\n\n"
        message += "<b>Next sending time:</b>\n"
        message += f"{next_trigger_time}\n\n"
        message += f"<b>Frequency:</b>\n"
        message += f"{reminder['printed_frequency']} at {utils.convert_time_str(reminder['time'], self.database.query_for_timezone())}"

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
            message += f"{'🖼' if 'file_id' in reminder else '🗓'}{number}){' '*(8 - 2*(len(str(number)) - 1))}{reminder['reminder_text']} ({reminder['printed_frequency']} at {utils.convert_time_str(reminder['time'], self.database.query_for_timezone())})\n"

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
    def __init__(self, chat_id: int, db: Database):
        self.chat_id = chat_id
        self.database = db

    def process_message(self, text: str) -> None:
        if text == "🕐 Change time zone":
            return self.set_timezone_message()
        else:
            return self.set_timezone(text)

    def list_settings(self) -> None:
        timezone = self.database.query_for_timezone()
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

        self.database.update_chat_settings(update_settings=True)
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
            self.database.update_chat_settings(update_settings=False,
                                               timezone=timezone)
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


class RenewReminderMenu:
    '''
    Instantiate a class to handle all the keyboard buttons when displaying a reminder.
    The buttons will automatically set another once-off reminder at the specified duration.
    '''
    def __init__(self, chat_id: int, database: Database):
        self.chat_id = chat_id
        self.database = database
        self.REMIND_AGAIN_TEXT = '\n\n\nRemind me again in:'

    def renew_reminder(self,
                       minutes: int,
                       reminder_text: str,
                       file_id: str = None):
        reminder_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        timezone = self.database.query_for_timezone()
        reminder_datetime = pytz.utc.localize(datetime.now() +
                                              timedelta(minutes=minutes))
        scheduler.add_job(utils.reminder_trigger,
                          'date',
                          run_date=reminder_datetime,
                          args=[self.chat_id, reminder_id],
                          id=job_id)
        reminder = {
            "reminder_id": reminder_id,
            "reminder_text": reminder_text,
            "frequency":
            reminder_datetime.strftime(f'{REMINDER_ONCE} %Y-%m-%d'),
            "time": reminder_datetime.strftime('%H:%M'),
            "job_id": job_id
        }
        if file_id is not None:
            reminder['field_id'] = file_id

        self.database.insert_reminder(reminder)
        reminder_datetime = reminder_datetime.astimezone(
            pytz.timezone(timezone))
        message = reminder_text + f"\n\n\nI will remind you again on {reminder_datetime.strftime('%a, %-d %B %Y at %H:%M:%S')}"
        return message, None, None

    def process(
            self,
            callback_query: Munch) -> Tuple[str, InlineKeyboardMarkup, str]:
        _, _time = callback_query.data.split("_")
        field_id = None if 'file_id' not in callback_query.message else callback_query.message.file_id
        reminder_text = callback_query.message.text[1:-len(self.
                                                           REMIND_AGAIN_TEXT)]
        if _time == '15m':
            return self.renew_reminder(minutes=15,
                                       reminder_text=reminder_text,
                                       file_id=field_id)
        elif _time == '30m':
            return self.renew_reminder(minutes=30,
                                       reminder_text=reminder_text,
                                       file_id=field_id)
        elif _time == '1h':
            return self.renew_reminder(minutes=60,
                                       reminder_text=reminder_text,
                                       file_id=field_id)
        elif _time == '3h':
            return self.renew_reminder(minutes=180,
                                       reminder_text=reminder_text,
                                       file_id=field_id)
        elif _time == '1d':
            return self.renew_reminder(minutes=24 * 60,
                                       reminder_text=reminder_text,
                                       file_id=field_id)
        elif _time == 'time':
            callback_query.message['from'] = callback_query['from']
            ReminderBuilder(self.database).process_message(callback_query)
            return callback_query.message.text[:-len(self.REMIND_AGAIN_TEXT
                                                     )], None, None

        elif _time == 'cancel':
            return callback_query.message.text[:-len(self.REMIND_AGAIN_TEXT
                                                     )], None, None

    def build(self, reminder_text: str, image: bool = False):
        message = reminder_text + self.REMIND_AGAIN_TEXT

        inline_buttons = []
        if image:
            inline_buttons.append([
                InlineKeyboardButton(text="15m", callback_data="renew_15m"),
                InlineKeyboardButton(text="30m", callback_data="renew_30m"),
            ])
            inline_buttons.append([
                InlineKeyboardButton(text="1h", callback_data="renew_1h"),
                InlineKeyboardButton(text="3h", callback_data="renew_3h"),
                InlineKeyboardButton(text="1d", callback_data="renew_1d")
            ])
        else:
            inline_buttons.append([
                InlineKeyboardButton(text="15m", callback_data="renew_15m"),
                InlineKeyboardButton(text="30m", callback_data="renew_30m"),
                InlineKeyboardButton(text="1h", callback_data="renew_1h"),
                InlineKeyboardButton(text="3h", callback_data="renew_3h"),
                InlineKeyboardButton(text="1d", callback_data="renew_1d")
            ])
        inline_buttons.append([
            InlineKeyboardButton(text="Enter Time",
                                 callback_data="renew_time"),
            InlineKeyboardButton(text="Cancel", callback_data="renew_cancel")
        ])
        markup = InlineKeyboardMarkup(inline_buttons)

        return message, markup, None
