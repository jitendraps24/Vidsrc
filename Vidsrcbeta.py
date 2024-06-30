import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import requests
from bs4 import BeautifulSoup
import re


def search_imdb(search_query):
    url = f"https://www.imdb.com/find?q={search_query}&s=tt&ref_=fn_al_tt_mr"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        for item in soup.select('li.ipc-metadata-list-summary-item'):
            title_tag = item.select_one('a.ipc-metadata-list-summary-item__t')
            year_tag = item.select_one(
                'span.ipc-metadata-list-summary-item__li')
            type_tag = item.select(
                'span.ipc-metadata-list-summary-item__li')[1] if len(
                    item.select('span.ipc-metadata-list-summary-item__li')
                ) > 1 else None

            if title_tag and year_tag:
                title = title_tag.text.strip()
                year = year_tag.text.strip()
                result_type = type_tag.text.strip() if type_tag else "Movie"
                imdb_id = re.search(r'/title/(tt\d+)/', title_tag['href'])
                if imdb_id:
                    results.append({
                        'title': title,
                        'year': year,
                        'type': result_type,
                        'imdb_id': imdb_id.group(1)
                    })
        return results
    except requests.RequestException as e:
        print(f"An error occurred while fetching the page: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return []


TITLE, SELECTION, SEASON, EPISODE = range(4)


async def start(update: telegram.Update,
                context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Welcome! Please enter a movie or TV show title to search:")
    return TITLE


async def handle_title(update: telegram.Update,
                       context: ContextTypes.DEFAULT_TYPE) -> int:
    search_query = update.message.text
    results = search_imdb(search_query)
    if not results:
        await update.message.reply_text(
            "No results found or an error occurred. Please try again.")
        return ConversationHandler.END

    context.user_data['results'] = results
    reply = "Showing up to 8 results:\n"
    for i, result in enumerate(results[:7], 1):
        reply += f"{i}. {result['title']} ({result['year']}) - {result['type']}\n"
    if len(results) > 7:
        reply += "8. Show all results"

    await update.message.reply_text(reply)
    await update.message.reply_text(
        "Enter the number of the result you want to see the IMDb ID for:")
    return SELECTION


async def handle_selection(update: telegram.Update,
                           context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        selection = int(update.message.text)
        results = context.user_data['results']
        if 1 <= selection <= 7:
            selected_result = results[selection - 1]
            context.user_data['selected_result'] = selected_result
            reply = f"Selected: {selected_result['title']} ({selected_result['year']}) - {selected_result['type']}\n"
            reply += f"IMDb ID: {selected_result['imdb_id']}\n"

            if selected_result['type'] == "TV Series":
                await update.message.reply_text(
                    reply +
                    "Enter the number of the season you want to watch:")
                return SEASON
            else:
                movie_link = f"https://vidsrc.me/embed/movie/{selected_result['imdb_id']}"
                reply += f"Movie link: {movie_link}"
                await update.message.reply_text(reply)
                await update.message.reply_text("Search again /start")
                return ConversationHandler.END
        elif selection == 8 and len(results) > 7:
            reply = "Showing all results:\n"
            for i, result in enumerate(results, 1):
                reply += f"{i}. {result['title']} ({result['year']}) - {result['type']}\n"
            await update.message.reply_text(reply)
            await update.message.reply_text(
                "Enter the number of the result you want to see the IMDb ID for:"
            )
            return SELECTION
        else:
            await update.message.reply_text("Invalid number. Please try again."
                                            )
            return SELECTION
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return SELECTION


async def handle_season(update: telegram.Update,
                        context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        season = int(update.message.text)
        context.user_data['season'] = season
        await update.message.reply_text(
            "Enter the number of the episode you want to watch:")
        return EPISODE
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number for the season.")
        return SEASON


async def handle_episode(update: telegram.Update,
                         context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        episode = int(update.message.text)
        selected_result = context.user_data['selected_result']
        season = context.user_data['season']
        movie_link = f"https://vidsrc.me/embed/tv/{selected_result['imdb_id']}/{season}/{episode}"
        reply = f"TV Series link: {movie_link}"
        await update.message.reply_text(reply)
        await update.message.reply_text("Search again /start")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number for the episode.")
        return EPISODE


async def cancel(update: telegram.Update,
                 context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


def main() -> None:
    # Replace 'YOUR_TOKEN' with your actual bot token
    application = Application.builder().token(
        "7104591151:AAGKQMJhSD9C20mNTkpU1rK1UYgdvbhu0lg").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TITLE:
            [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_title)],
            SELECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               handle_selection)
            ],
            SEASON:
            [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_season)],
            EPISODE:
            [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_episode)],
        },
        fallbacks=[CommandHandler('cancel', cancel)])

    application.add_handler(conv_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
