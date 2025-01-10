import os
import logging
import datetime
import aiohttp
import pandas as pd
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from io import StringIO
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackContext, CallbackQueryHandler

# Load environment variables from the .env file
load_dotenv()

# Get the token from the .env file
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FOOTBALL_TEAMS_API = os.getenv("FOOTBALL_TEAMS_API")
FOOTBALL_DATA_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN")
FOOTBALL_SCORES_API = os.getenv("FOOTBALL_SCORES_API")
TIMER = 300

TODAY = datetime.datetime.now().strftime("%d-%m-%Y")

#results storage
OLD_TABLE = {}

# Set up logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    welcome_message = (
        f"👋 *Benvenuto, {update.effective_user.first_name}!* 🎉\n\n"
        "Sono un bot qui per aiutarti con notifiche e controlli sui risultati sportivi.\n\n"
        "📚 *Per iniziare*: Usa i comandi disponibili:\n"
        "➡️ /aiuto - Scopri tutte le funzionalità che posso offrirti!\n\n"
        "💡 *Consiglio*: Configura le tue preferenze per sfruttare al meglio il bot!"
    )
    # Definisci il menu
    keyboard = [
        [InlineKeyboardButton("📖 Aiuto", callback_data='aiuto')],
        [InlineKeyboardButton("⚽ Codici Squadre", callback_data='squadre')],
        [InlineKeyboardButton("⏱ Imposta Timer", callback_data='timer')],
        [InlineKeyboardButton("✅ Inizia Monitoraggio", callback_data='imposta')],
        [InlineKeyboardButton("⏹ Ferma Monitoraggio", callback_data='stop')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome_message,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle menu button clicks."""
    query = update.callback_query
    await query.answer()  # Conferma l'interazione col pulsante

    if query.data == 'aiuto':
        await help_command(update=update, context=context)
    elif query.data == 'squadre':
        await get_codes_teams(update, context)
    elif query.data == 'timer':
        await query.edit_message_text("Utilizzo: /timer <minuti>")
    elif query.data == 'imposta':
        await query.edit_message_text("Utilizzo: /imposta <Squadra> <Numero> <Esito desiderato>")
    elif query.data == 'stop':
        await stop_all(update, context)
    else:
        await query.edit_message_text("Comando non riconosciuto.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /aiuto is issued."""
    help_msg = (
        "📖 *Benvenuto nella guida del bot!*\n\n"
        "Ecco la lista dei comandi disponibili:\n\n"
        "✅ /start - Avvia il bot e inizia a utilizzarlo\n"
        "⏹ /stop - Ferma tutti i risultati pianificati\n"
        "⚽ /imposta <CodiceSquadra> <Numero> <Esito>\n"
        "   _Esempio_: /imposta ROM 2 Perdita\n"
        "   Ricevi notifiche quando la tua squadra (es: Roma) perde due volte consecutive\n"
        "⏱ /timer <minuti> - Imposta l'intervallo di controllo dei risultati\n"
        "   _Default_: 3 minuti\n"
        "📋 /squadre - Mostra l'elenco delle squadre disponibili con i rispettivi codici\n"
        "ℹ️ /aiuto - Mostra questa guida\n\n"
        "💡 *Suggerimento*: Usa i comandi esattamente come indicato per ottenere il massimo dal bot!"
    )

    if update.message:  # If the message exists, respond with the help message
        await update.message.reply_text(
            help_msg,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    elif update.callback_query:  # If the callback query exists (as it might happen in the menu)
        await update.callback_query.message.reply_text(
            help_msg,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )


async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set global timer"""

    try:
        # args[0] should contain the time for the timer in minutes
        minutes = float(context.args[0])
        seconds = minutes * 60

        if seconds < 0:
            await update.effective_message.reply_text("mi dispiace, non possiamo tornare al futuro!")
            return

        await stop_all(update=update, context=context)
        global TIMER
        TIMER = seconds
        text = "Timer impostato con successo!\n Reimposta la squadra!"

        await update.effective_message.reply_text(text)

    except (IndexError, ValueError):
        await update.effective_message.reply_text("Usage: /timer <minutes>")


async def get_codes_teams(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with aiohttp.ClientSession() as client:
        res = await client.get(FOOTBALL_TEAMS_API, headers={"X-Auth-Token": FOOTBALL_DATA_TOKEN})
        logger.info(res.status)
        data = await res.json()
        teams_list = []

        for items in data['teams']:
            team_name = items['name']
            team_code = items['tla']
            teams_list.append([team_name, team_code])

        teams_df = pd.DataFrame(teams_list, columns=['Nome squadra', 'Codice squadra'])
        logger.info(teams_df)

        output = StringIO()
        teams_df.to_csv(output, index=True, sep='\t')
        output.seek(0)

        # await update.message.reply_document(document=output, filename="squadre.txt")
        if update.message:  # If the message exists, respond with the squadre message
            await update.message.reply_document(document=output, filename="squadre.txt")
        elif update.callback_query:  # If the callback query exists (as it might happen in the menu)
            await update.callback_query.message.reply_document(document=output, filename="squadre.txt")


async def get_all_matchs():
    async with aiohttp.ClientSession() as client:
        headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "Connection" : "keep-alive",
            "Access-Control-Allow-Headers":"Keep-Alive,User-Agent,X-Requested-With,Cache-Control,Content-Type,Authorization,user_data,pragma,channel,tokenKeep-Alive,User-Agent,X-Requested-With,Cache-Control,Content-Type,Authorization,user_data,pragma,channel,token",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"
        }
        
        request_url = os.path.join(FOOTBALL_SCORES_API, TODAY)
        response = await client.get(request_url, headers=headers)
        if response.status == 200:
            results = await response.json()
            return results
        logger.info(f"Errore nell'ottenere i dati: {response.status}")
        return []


async def verifica_esito_consecutive(lista_dizionari, n, esito):
    count = 0
    ultime_partite = lista_dizionari[:n]  # Prendi le ultime n partite
    for partita in ultime_partite:
        if partita['esito'].lower() == esito:
            count += 1
        else:
            return False  # Se trovi una partita che non è una vittoria, restituisci False
    return count == n  # Restituisce True solo se tutte le n partite sono vittorie


async def format_table_as_markdown(data):
    table = "```\n"
    headers = "home_team | away_team | risultato | data"
    table += headers + "\n"
    table += "-" * len(headers) + "\n"
    for item in data:
        row = f"{item['home_team']} | {item['away_team']} | {item['risultato']} | {item['data']}"
        table += row + "\n"
    table += "```"
    return table


async def check_results(context: CallbackContext):
    data = context.job.data
    team, numero, desired_outcome = data.split('-')
    numero = int(numero)
    logger.info(f"{team} {numero} {desired_outcome}")
    output = []
    outcome = ""
    desired_outcome = desired_outcome.lower()

    all_matchs = await get_all_matchs()
    for data_dict in all_matchs:
        outcome = ""
        home_team, away_team = data_dict['descrizioneAvventimento'].split(' - ')
        single_data = {
            'home_team': home_team,
            'away_team': away_team
                       
        }
        score_home, score_away = map(int, data_dict['risultato'].split('-'))

        if (home_team == team and score_home == score_away) or \
           (away_team == team and score_home == score_away):
            outcome = "Pareggio"
            single_data['esito'] = outcome
            single_data['data'] = f"{TODAY}H{data_dict['dataOra']}"
            single_data['partita'] = data_dict['descrizioneAvventimento']
            single_data['risultato'] = data_dict['risultato']
            single_data['partita_id'] = f"{data_dict['codicePalinsesto']}_{data_dict['codiceAvvenimento']}"

        elif (home_team == team and score_home > score_away) or \
             (away_team == team and score_home < score_away):
            outcome = "Vittoria"
            single_data['esito'] = outcome
            single_data['data'] = f"{TODAY}H{data_dict['dataOra']}"
            single_data['partita'] = data_dict['descrizioneAvventimento']
            single_data['risultato'] = data_dict['risultato']
            single_data['partita_id'] = f"{data_dict['codicePalinsesto']}_{data_dict['codiceAvvenimento']}"
        elif (home_team == team and score_home < score_away) or \
             (away_team == team and score_home > score_away):
            outcome = "Perdita"
            single_data['esito'] = outcome
            single_data['data'] = f"{TODAY}H{data_dict['dataOra']}"
            single_data['partita'] = data_dict['descrizioneAvventimento']
            single_data['risultato'] = data_dict['risultato']
            single_data['partita_id'] = f"{data_dict['codicePalinsesto']}_{data_dict['codiceAvvenimento']}"

        if outcome:
            output.append(single_data)

    if output:
        logger.info(output)
        if await verifica_esito_consecutive(output, numero, desired_outcome):
            ultime_partite = output[:numero]
            new_table = await format_table_as_markdown(ultime_partite)
            global OLD_TABLE
            if new_table != OLD_TABLE.get(data, None):
                await context.bot.send_message(chat_id=context.job.chat_id, text=data)
                await context.bot.send_message(chat_id=context.job.chat_id, text=new_table, parse_mode="Markdown")
                OLD_TABLE[data] = new_table
            else:
                logger.info("same output as the last one")
        else:
            logger.info("Any output available")
    else:
        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=f"Risultati not found now!"
        )
    logger.info(OLD_TABLE)


async def start_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0 or len(context.args) > 3:
        await update.message.reply_text("Utilizzo corretto: /imposta <Squadra> <Numero> <Esito desiderato>")
        return

    try:
        team, numero = context.args[:-1]
        desired_outcome = context.args[-1]
    except Exception as e:
        logger.info(e, "Setting default arguments")
        numero = 3
        desired_outcome = "vittoria"

    chat_id = update.message.chat_id
    data = f"{team}-{numero}-{desired_outcome}"
    # stop all running job 
    # await stop_all(update=update, context=context)
    # schedule the new job
    context.job_queue.run_repeating(check_results, first=1, interval=TIMER, data=data, chat_id=chat_id, name=f"{chat_id}-{data}")
    logger.info("Job added")
    logger.info(f"Inizio monitoraggio risultati per la squadra {str(team)}\nEsito desiderato: {desired_outcome}\nNumero di esito consecutive: {numero}")

    await update.message.reply_text(f"Inizio monitoraggio risultati per la squadra {str(team)}\nEsito desiderato: {desired_outcome}\nNumero di esito consecutive: {numero}")


async def stop_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    logger.info(context.job_queue.jobs())
    try:
        await context.job_queue.stop()
        logger.info("Tutti i monitoraggi sono stati fermati.")
        stop_msg = "L'invio delle notifiche è stato fermato"
        if update.message:  # If the message exists, respond with the help message
            await update.message.reply_text(stop_msg)
        elif update.callback_query:  # If the callback query exists (as it might happen in the menu)
            await update.callback_query.message.reply_text(stop_msg)
        # await update.message.reply_text("L'invio delle notifiche è stato fermato")  # no longer use
        global OLD_TABLE
        OLD_TABLE.clear()
        await context.job_queue.start()
    except Exception as e:
        logger.info(e)
    

def main():
    """Start the bot."""
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler('squadre', get_codes_teams))
    app.add_handler(CallbackQueryHandler(menu_callback))  # Gestisce i pulsanti del menu
    app.add_handler(CommandHandler("aiuto", help_command))
    app.add_handler(CommandHandler('imposta', start_monitoring))
    app.add_handler(CommandHandler("stop", stop_all))
    app.add_handler(CommandHandler("timer", set_timer))
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
