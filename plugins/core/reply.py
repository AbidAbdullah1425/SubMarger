# DIEOAJJSSS






@Bot.on_message(
    filters.user(OWNER_ID) &
    (filters.video | (filters.document & filters.create(lambda _, __, m: m.document and (m.document.file_name.endswith((".ass", ".srt"))))))
)
async def handle_reply(client: Client, message: Message):
    