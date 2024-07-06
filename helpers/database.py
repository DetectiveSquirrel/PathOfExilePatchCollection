import sqlite3
import settings


async def clear_tables():
    try:
        # Select and count rows before deleting
        settings.CURSOR.execute("SELECT COUNT(*) FROM message_log")
        message_log_count = settings.CURSOR.fetchone()[0]

        settings.CURSOR.execute("SELECT COUNT(*) FROM patch")
        patch_count = settings.CURSOR.fetchone()[0]

        # Delete the rows
        settings.CURSOR.execute("DELETE FROM message_log")
        settings.CURSOR.execute("DELETE FROM patch")
        settings.CONN.commit()

        # Format the response
        response = f"Cleared the following data:\n\n"
        response += f"message_log table: {message_log_count} rows\n"
        response += f"patch table: {patch_count} rows\n"

        return response

    except sqlite3.Error as e:
        return f"An error occurred: {e}"
