from app import commands
'''
start - Help on how to use this Bot
help - Help on how to use this Bot
delete - Reply to a message with this command to initiate poll to delete
getconfig - Get current threshold and expiry time for this group chat
setthreshold - Set a threshold for this group chat
setexpiry - Set a expiry time for the poll
support - Support me on github!
'''
COMMANDS = {
    '/start': commands.start,
    '/help': commands.start,
    '/support': commands.support,
    '/remind': commands.remind,
    '/list': commands.list_reminders
}
