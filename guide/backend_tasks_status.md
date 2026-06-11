# Telegram Bot Backend Tasks Status & Implementation Guide

This document reviews the 5 backend tasks, checks what is currently implemented in your codebase (`bot.py` and `database.py`), identifies any gaps/bugs, and outlines what needs to be done to complete them.

---

## 📋 Task Overview & Status Summary

| Task | Description | Status | Missing / Action Required |
| :--- | :--- | :---: | :--- |
| **Task 1** | Save Mentioned Messages (`@botusername`) | ⚠️ **Partially Implemented** | Startup crash risk; does not handle edited mentions or media caption mentions. |
| **Task 2** | Save Group Creator / Adder Info | ⚠️ **Partially Implemented** | Stores the adder, but does not capture group owner (creator) info if they differ. |
| **Task 3** | `/admin` Command | ❌ **Incomplete** | Missing Admin (Creator) Name and Username fields in both the schema and output. |
| **Task 4** | Message Counter (Middleware) | ⚠️ **Partially Implemented** | Non-atomic database updates; counting could be optimized into a single `UPSERT`. |
| **Task 5** | `/totalmsg` Command |  **Fully Implemented** | No action required. Code correctly formats and responds based on chat type. |
| **Task 6** | Broadcast System (`/broadcast`) | ❌ **Incomplete** | Missing admin authorization, `/broadcast` command handler, and database queries to fetch active chats. |

---

## 🔍 Detailed Task Breakdown

### 🛠️ Task 1: Save Mentioned Messages
* **Goal**: When a user mentions the bot, save details (Message ID, Message Text, User ID, Username, First Name, Group ID, Group Name, Date/Time).
* **What is Done**:
  - The `mentions` table schema exists in `database.py` with all required fields.
  - `save_mention()` correctly performs the insert query.
  - `bot.py` uses a regex/text check handler to detect the bot's username and call `save_mention()`.
* **What is Missing / Issues**:
  1. **Startup Crash Risk**: In `bot.py` (Line 433), the handler condition calls `bot.get_me().username` during compilation. If the bot token is invalid or there is no network connection during script load, the bot will crash immediately before starting.
  2. **Edited Messages / Caption Mentions**: The handler only listens to normal text messages. It does not trigger if a user edits their message to include a mention, or if the mention is in a photo/document caption.
* **To Be Done**:
  - Make the mention-checking condition dynamic or cache the username inside the handler function rather than calling `bot.get_me()` inside the decorator logic.

---

### 🛠️ Task 2: Save Group Creator Information
* **Goal**: When the bot is added to a group, save Group ID, Group Name, User ID of the person that added the bot, Username, Full Name, and Date Added.
* **What is Done**:
  - The `groups` table schema exists in `database.py`.
  - `bot.py` utilizes `@bot.my_chat_member_handler()` to detect when the bot joins a group and extracts the user who added it (`update.from_user`).
* **What is Missing / Issues**:
  - **Adder vs. Creator**: The code correctly saves the user who **added** the bot. However, the task title is *"Save Group Creator Information"*. If you need the group's actual creator/owner (who might be different from the person who added the bot), this information is not retrieved.
  - **Re-invite Handling**: If the bot is removed and re-added by a different user, the `ON CONFLICT (group_id) DO NOTHING` constraint will prevent the database from updating the adder info to the new user.
* **To Be Done**:
  - Decide if you need the actual group *creator* (requires fetching chat administrators using Telegram API `get_chat_administrators` and finding the owner) or if saving the *adder* is sufficient.

---

### 🛠️ Task 3: /admin Command
* **Goal**: When a user sends `/admin` in a group, reply with:
  ```text
  Admin Name: John Doe
  Username: @johndoe

  Added By:
  Name: Peter James
  Username: @peterjames
  ```
* **What is Done**:
  - The command is registered in `bot.py` and checks group info from the database.
* **What is Missing / Issues**:
  - **Missing Admin Fields**: The database `groups` table does **not** store the Group Admin's Name or Username. It only stores the "Added By" (adder) details.
  - **Missing Output**: The reply message printed by `/admin` currently only displays the group name, adder's name, adder's username, and date added. It does not display the Admin details.
* **To Be Done**:
  1. Add `admin_name` and `admin_username` columns to the `groups` table in `database.py`.
  2. When the bot is added to a group (Task 2), query Telegram for the group creator/admin and save it.
  3. Update `/admin` handler to format the response exactly as specified.

---

### 🛠️ Task 4: Message Counter
* **Goal**: Count every message received. Count group messages per group, and private messages per user.
* **What is Done**:
  - A `message_counts` table is present.
  - A middleware handler intercepts incoming messages and calls `count_message()`.
* **What is Missing / Issues**:
  - **Non-Atomic Queries**: `count_message()` runs two queries: an `INSERT ... ON CONFLICT DO NOTHING` followed by an `UPDATE`. Under high concurrent message volume, this is inefficient and can cause minor database locking issues.
* **To Be Done**:
  - Optimize the database interaction into a single atomic PostgreSQL `UPSERT` statement:
    ```sql
    INSERT INTO message_counts (chat_id, chat_type, chat_name, message_count)
    VALUES (%s, %s, %s, 1)
    ON CONFLICT (chat_id) 
    DO UPDATE SET 
        message_count = message_counts.message_count + 1,
        last_updated = CURRENT_TIMESTAMP;
    ```

---

### 🛠️ Task 5: /totalmsg Command
* **Goal**: Reply with formatted total messages (`Total Messages in this Group: 1,250` or `Your Total Messages: 350`) depending on whether it is a group or private chat.
* **What is Done**:
  - `get_message_count()` correctly queries the table.
  - `/totalmsg` formats the output using Python's `{total:,}` for comma separation and replies with the correct context.
* **What is Missing / Issues**:
  - *None.* This task is fully implemented and functions as expected.

---

### 🛠️ Task 6: Broadcast System
* **Goal**: An admin-only command `/broadcast <message>` that sends the text message to all users who have started the bot (private chats) and all groups the bot is in.
* **What is Done**:
  - *Nothing.* This is a new requirement.
* **What is Missing / Issues**:
  1. **Admin Authorization**: The bot needs to know who the authorized admin is (e.g., matching the user's Telegram ID against an `ADMIN_USER_ID` environment variable).
  2. **Recipient Retrieval**: The database needs to be queried to get all unique group IDs and private user chat IDs. Currently, this can be done by selecting unique `chat_id` values from the `message_counts` table.
  3. **Broadcasting Logic**: A loop that iterates through all recipient IDs and uses `bot.send_message()` to broadcast the message, with error handling to catch and skip cases where the bot was blocked or removed.
* **To Be Done**:
  1. Define a function in `database.py` to retrieve all unique active chat IDs:
     ```python
     def get_all_chats():
         conn = get_connection()
         cursor = conn.cursor()
         cursor.execute("SELECT chat_id FROM message_counts")
         rows = cursor.fetchall()
         conn.close()
         return [row["chat_id"] for row in rows]
     ```
  2. In `.env`, define an `ADMIN_USER_ID` variable:
     ```env
     ADMIN_USER_ID="123456789"
     ```
  3. In `bot.py`, add a `/broadcast` command handler:
     ```python
     @bot.message_handler(commands=["broadcast"])
     def handle_broadcast(message):
         admin_id = os.getenv("ADMIN_USER_ID")
         if not admin_id or str(message.from_user.id) != str(admin_id):
             bot.reply_to(message, "❌ Unauthorized: Only the bot admin can use this command.")
             return
         
         # Extract the message text after the command
         command_parts = message.text.split(" ", 1)
         if len(command_parts) < 2:
             bot.reply_to(message, "⚠️ Usage: /broadcast <your message>")
             return
         
         broadcast_text = command_parts[1]
         chat_ids = get_all_chats() # From database.py
         
         success_count = 0
         fail_count = 0
         
         for chat_id in chat_ids:
             try:
                 bot.send_message(chat_id, broadcast_text)
                 success_count += 1
             except Exception as e:
                 # Handles blocked bots, kicked from groups, etc.
                 fail_count += 1
         
         bot.reply_to(message, f"📢 Broadcast completed!\n✅ Sent: {success_count}\n❌ Failed: {fail_count}")
     ```

